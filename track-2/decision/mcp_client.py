from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from decision.contracts import ToolCallRecord

SENSITIVE = re.compile(r"(authorization|api[_-]?key|token|secret|password|cookie)", re.I)
ID_KEY = re.compile(r"(^id$|_id$|Id$|Ids$|_ids$)")


def _safe(value: Any, key: str = "") -> Any:
    if SENSITIVE.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _safe(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe(v, key) for v in value]
    if ID_KEY.search(key) and isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return value


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


class McpSession:
    """Version-isolated FastMCP stdio client with bounded, auditable calls."""

    def __init__(self, data_dir: Path, total_timeout_sec: float = 120,
                 per_call_timeout_sec: float = 20, max_business_calls: int = 25,
                 client: Any | None = None, raw_dir: Path | None = None):
        self.data_dir = Path(data_dir).resolve()
        self.total_timeout_sec = total_timeout_sec
        self.per_call_timeout_sec = per_call_timeout_sec
        self.max_business_calls = max_business_calls
        self._client = client
        self._entered = None
        self._started = 0.0
        self._business_calls = 0
        self.records: list[ToolCallRecord] = []
        self.available_tools: set[str] = set()
        self.raw_dir = Path(raw_dir) if raw_dir else None

    def _new_record(self, tool_name: str, arguments: dict, started: str,
                    began: float, status: str, result=None, error=None) -> ToolCallRecord:
        return ToolCallRecord(
            call_id=f"call-{len(self.records) + 1:03d}-{uuid.uuid4().hex[:8]}",
            sequence=len(self.records) + 1, tool_name=tool_name,
            arguments=_safe(arguments), started_at_utc=started,
            duration_ms=max(0, round((time.monotonic() - began) * 1000)),
            status=status, result=_safe(result) if isinstance(result, dict) else None,
            error=_safe(str(error), "error") if error else None,
        )

    async def __aenter__(self):
        self._started = time.monotonic()
        if self._client is None:
            from fastmcp import Client
            from fastmcp.client.transports import StdioTransport
            code_root = Path(__file__).resolve().parents[1]
            env = os.environ.copy()
            env["MGAI_DATA_DIR"] = str(self.data_dir)
            transport = StdioTransport(sys.executable, ["-m", "mcp_layer.server"],
                                       env=env, cwd=str(code_root))
            self._client = Client(transport, timeout=self.per_call_timeout_sec,
                                  init_timeout=min(self.per_call_timeout_sec, self.total_timeout_sec))
        self._entered = await self._client.__aenter__()
        began = time.monotonic()
        started = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            async with asyncio.timeout(self._remaining_timeout()):
                tools = await self._client.list_tools()
            names = [str(t.name) for t in tools]
            self.available_tools = set(names)
            rec = self._new_record("tools/list", {}, started, began, "success", {"tools": names})
        except TimeoutError:
            rec = self._new_record("tools/list", {}, started, began, "timeout", error="tools/list timed out")
        except Exception as exc:
            rec = self._new_record("tools/list", {}, started, began, "error", error=exc)
        self.records.append(rec)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc, tb)

    def _remaining_timeout(self) -> float:
        remaining = self.total_timeout_sec - (time.monotonic() - self._started)
        return max(0.001, min(self.per_call_timeout_sec, remaining))

    def _extract(self, response: Any) -> tuple[dict | None, str | None]:
        structured = getattr(response, "structured_content", None)
        if isinstance(structured, dict):
            return structured, None
        texts = [getattr(item, "text", None) for item in getattr(response, "content", [])]
        text = "\n".join(x for x in texts if isinstance(x, str))
        if text:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return None, "MCP returned non-JSON text without structured content"
            return parsed if isinstance(parsed, dict) else {"value": parsed}, None
        return None, "MCP returned no structured or JSON result"

    def _write_raw(self, record: ToolCallRecord, response: Any) -> None:
        if self.raw_dir is None:
            return
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        payload = {"tool_name": record.tool_name, "arguments": record.arguments,
                   "response": _jsonable(response)}
        try:
            (self.raw_dir / f"{record.call_id}.json").write_text(
                json.dumps(payload, ensure_ascii=False, default=str, allow_nan=False))
        except Exception:
            pass

    async def call(self, tool_name: str, arguments: dict) -> ToolCallRecord:
        began = time.monotonic()
        started = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        if self._business_calls >= self.max_business_calls:
            rec = self._new_record(tool_name, arguments, started, began, "error",
                                   error=f"business tools/call limit {self.max_business_calls} reached")
            self.records.append(rec)
            return rec
        self._business_calls += 1
        response = None
        try:
            async with asyncio.timeout(self._remaining_timeout()):
                response = await self._client.call_tool(tool_name, arguments, raise_on_error=False)
            result, parse_error = self._extract(response)
            is_error = bool(getattr(response, "is_error", False))
            if is_error or parse_error:
                rec = self._new_record(tool_name, arguments, started, began, "error",
                                       result=result, error=parse_error or "MCP tool returned isError=true")
            else:
                rec = self._new_record(tool_name, arguments, started, began, "success", result=result)
        except TimeoutError:
            rec = self._new_record(tool_name, arguments, started, began, "timeout",
                                   error=f"tool call exceeded {self._remaining_timeout():.3f}s budget")
        except Exception as exc:
            rec = self._new_record(tool_name, arguments, started, began, "error", error=exc)
        self.records.append(rec)
        self._write_raw(rec, response)
        return rec
