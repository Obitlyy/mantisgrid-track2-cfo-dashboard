from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import threading
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import Callable

from decision.config import RuntimePaths, resolve_paths
from decision.contracts import Evaluation, Investigation
from decision.data import DataSnapshot, load_snapshot
from decision.errors import DecisionError
from decision.investigation import (
    load_investigation,
    not_run_investigation,
    run_investigation,
)


LOG = logging.getLogger(__name__)


class EvaluationCache:
    """A small thread-safe LRU whose values never escape by reference."""

    def __init__(self, maxsize: int = 64):
        self._maxsize = maxsize
        self._values: OrderedDict[str, Evaluation] = OrderedDict()
        self._lock = threading.RLock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._values)

    def get_or_create(self, key: str, factory: Callable[[], Evaluation]) -> Evaluation:
        with self._lock:
            value = self._values.get(key)
            if value is None:
                value = factory()
                self._values[key] = value.model_copy(deep=True)
                if len(self._values) > self._maxsize:
                    self._values.popitem(last=False)
            else:
                self._values.move_to_end(key)
            return value.model_copy(deep=True)


def bootstrap_paths() -> RuntimePaths:
    return resolve_paths()


def _failure_details(exc: Exception) -> tuple[str, str, dict]:
    if isinstance(exc, DecisionError):
        return exc.code, exc.message, exc.details
    return "DATA_NOT_READY", "Decision analysis failed to initialize.", {
        "reason": str(exc)
    }


def _failed_audit(dataset_id: str, exc: Exception) -> Investigation:
    return not_run_investigation(dataset_id).model_copy(
        update={
            "status": "failed",
            "summary": "The automatic MCP investigation failed.",
            "limitations": [str(exc) or exc.__class__.__name__],
        }
    )


async def _run_audit(app, paths: RuntimePaths, snapshot: DataSnapshot) -> None:
    try:
        result = await asyncio.wait_for(
            run_investigation(
                paths.data_dir, paths.output_dir, snapshot=snapshot
            ),
            timeout=120,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        LOG.exception("Automatic Track 2 audit failed")
        result = _failed_audit(snapshot.dataset_id, exc)
    app.state.decision_investigation = result
    app.state.decision_audit_status = result.status


@asynccontextmanager
async def decision_lifespan(app):
    app.state.decision_snapshot = None
    app.state.decision_load_error = None
    app.state.decision_paths = None
    app.state.decision_investigation = None
    app.state.decision_audit_status = "not_run"
    app.state.decision_audit_task = None
    app.state.decision_evaluation_cache = EvaluationCache(maxsize=64)

    try:
        paths = resolve_paths()
        snapshot = load_snapshot(paths.data_dir)
    except Exception as exc:
        app.state.decision_load_error = _failure_details(exc)
    else:
        app.state.decision_paths = paths
        app.state.decision_snapshot = snapshot
        cached = load_investigation(paths.output_dir, snapshot.dataset_id)
        if cached is not None:
            app.state.decision_investigation = cached
            app.state.decision_audit_status = cached.status
        else:
            mode = os.environ.get("TRACK2_AUDIT_MODE", "auto").strip().lower()
            if mode == "auto":
                app.state.decision_audit_status = "running"
                app.state.decision_investigation = not_run_investigation(
                    snapshot.dataset_id
                ).model_copy(
                    update={
                        "status": "running",
                        "summary": "The automatic MCP investigation is running.",
                    }
                )
                app.state.decision_audit_task = asyncio.create_task(
                    _run_audit(app, paths, snapshot)
                )
            elif mode != "off":
                error = ValueError("TRACK2_AUDIT_MODE must be 'auto' or 'off'")
                app.state.decision_investigation = _failed_audit(
                    snapshot.dataset_id, error
                )
                app.state.decision_audit_status = "failed"

    try:
        yield
    finally:
        task = app.state.decision_audit_task
        if task is not None:
            if not task.done():
                task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


def snapshot_from_app(app) -> DataSnapshot:
    snapshot = getattr(app.state, "decision_snapshot", None)
    if snapshot is not None:
        return snapshot
    code, message, details = getattr(
        app.state,
        "decision_load_error",
        ("DATA_NOT_READY", "Decision analysis is not initialized.", {}),
    )
    raise DecisionError(code, message, details, 503)


def latest_investigation(app, snapshot: DataSnapshot) -> Investigation:
    paths = getattr(app.state, "decision_paths", None)
    if paths is not None:
        cached = load_investigation(paths.output_dir, snapshot.dataset_id)
        if cached is not None:
            app.state.decision_investigation = cached
            app.state.decision_audit_status = cached.status
            return cached
    current = getattr(app.state, "decision_investigation", None)
    if current is not None and current.dataset_id == snapshot.dataset_id:
        return current
    return not_run_investigation(snapshot.dataset_id)
