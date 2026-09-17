import asyncio
import json

import pytest

from decision.mcp_client import McpSession


class Result:
    def __init__(self, structured=None, text=None, is_error=False):
        self.structured_content = structured
        self.content = [] if text is None else [type("Text", (), {"text": text})()]
        self.is_error = is_error


class FakeClient:
    def __init__(self, results): self.results = iter(results)
    async def __aenter__(self): return self
    async def __aexit__(self, *args): return None
    async def list_tools(self): return [type("Tool", (), {"name": "health"})()]
    async def call_tool(self, name, arguments, **kwargs):
        value = next(self.results)
        if value == "sleep":
            await asyncio.sleep(1)
        return value


@pytest.mark.asyncio
async def test_records_tools_list_and_prefers_structured_result(tmp_path):
    session = McpSession(tmp_path, client=FakeClient([Result({"ok": True})]))
    async with session:
        record = await session.call("health", {})
    assert session.records[0].tool_name == "tools/list"
    assert record.result == {"ok": True}
    assert record.status == "success"


@pytest.mark.asyncio
async def test_parses_json_text_and_rejects_non_json(tmp_path):
    session = McpSession(tmp_path, client=FakeClient([Result(text='{"ok": true}'), Result(text="plain")]))
    async with session:
        good = await session.call("health", {})
        bad = await session.call("health", {})
    assert good.result == {"ok": True}
    assert bad.status == "error" and "non-JSON" in bad.error


@pytest.mark.asyncio
async def test_records_protocol_error_and_timeout(tmp_path):
    session = McpSession(tmp_path, per_call_timeout_sec=.01,
                         client=FakeClient([Result(text='{"error":"x"}', is_error=True), "sleep"]))
    async with session:
        errored = await session.call("health", {"token": "secret"})
        timed_out = await session.call("health", {})
    assert errored.status == "error"
    assert errored.arguments == {"token": "[REDACTED]"}
    assert timed_out.status == "timeout"


@pytest.mark.asyncio
async def test_enforces_25_business_call_limit(tmp_path):
    session = McpSession(tmp_path, client=FakeClient([Result({}) for _ in range(25)]))
    async with session:
        for _ in range(25):
            assert (await session.call("health", {})).status == "success"
        blocked = await session.call("health", {})
    assert blocked.status == "error"
    assert "25" in blocked.error
