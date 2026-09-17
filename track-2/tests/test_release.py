from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from fastapi.testclient import TestClient

from decision.audit_storage import audit_path, save_audit
from decision.config import RuntimePaths
from decision.investigation import not_run_investigation
from factories import default_request, golden_snapshot


def _completed_audit(dataset_id: str):
    return not_run_investigation(dataset_id).model_copy(
        update={
            "status": "completed",
            "verdict": "revise",
            "summary": "Cached audit completed.",
            "limitations": [],
        }
    )


def _configure_runtime(monkeypatch, tmp_path: Path, *, audit_mode: str = "off"):
    from decision import bootstrap

    snapshot = golden_snapshot()
    paths = RuntimePaths(data_dir=tmp_path / "data", output_dir=tmp_path / "out")
    loads: list[Path] = []

    def load_once(path: Path):
        loads.append(path)
        return snapshot

    monkeypatch.setenv("TRACK2_AUDIT_MODE", audit_mode)
    monkeypatch.setattr(bootstrap, "resolve_paths", lambda: paths)
    monkeypatch.setattr(bootstrap, "load_snapshot", load_once)
    return snapshot, paths, loads


def test_official_app_is_reused_and_decision_router_is_mounted_once():
    from api.main import app as official_app
    from decision.app import app

    assert app is official_app
    assert list(app.openapi()["paths"]).count("/v1/decision/health") == 1
    assert any(getattr(route, "path", None) == "/v1/events/findings" for route in app.routes)
    assert not any(getattr(route, "path", "").startswith("/decision-api") for route in app.routes)


def test_lifespan_loads_snapshot_once_and_preserves_official_validation(monkeypatch, tmp_path):
    from decision import bootstrap
    from decision.app import app

    snapshot, _, loads = _configure_runtime(monkeypatch, tmp_path)
    monkeypatch.setattr(bootstrap, "load_investigation", lambda *_: None)

    with TestClient(app) as client:
        first = client.get("/v1/decision/health")
        second = client.get("/v1/decision/health")
        official = client.post("/v1/causal", json={})

    assert len(loads) == 1
    assert first.status_code == second.status_code == 200
    assert first.json() == {
        "status": "ready",
        "schema_version": "1.0.0",
        "dataset_id": snapshot.dataset_id,
        "audit_status": "not_run",
    }
    assert official.status_code == 422
    assert "detail" in official.json()
    assert "error" not in official.json()


def test_lifespan_load_failure_is_honest_not_ready(monkeypatch, tmp_path):
    from decision import bootstrap
    from decision.app import app
    from decision.errors import DecisionError

    paths = RuntimePaths(data_dir=tmp_path / "data", output_dir=tmp_path / "out")
    monkeypatch.setenv("TRACK2_AUDIT_MODE", "off")
    monkeypatch.setattr(bootstrap, "resolve_paths", lambda: paths)
    monkeypatch.setattr(
        bootstrap,
        "load_snapshot",
        lambda _: (_ for _ in ()).throw(
            DecisionError("DATA_NOT_READY", "Official data files are missing.", {"missing": ["prepped/jobs.parquet"]}, 503)
        ),
    )

    with TestClient(app) as client:
        health = client.get("/v1/decision/health")
        evaluation = client.post(
            "/v1/decision/evaluate", json=default_request().model_dump(mode="json")
        )

    assert health.status_code == 503
    assert health.json()["status"] == "not_ready"
    assert evaluation.status_code == 503
    assert evaluation.json()["error"]["code"] == "DATA_NOT_READY"
    assert evaluation.json()["error"]["details"]["missing"] == ["prepped/jobs.parquet"]


def test_valid_cached_audit_is_visible_without_scheduling(monkeypatch, tmp_path):
    from decision import bootstrap
    from decision.app import app

    snapshot, _, _ = _configure_runtime(monkeypatch, tmp_path, audit_mode="auto")
    cached = _completed_audit(snapshot.dataset_id)
    monkeypatch.setattr(bootstrap, "load_investigation", lambda *_: cached)

    async def must_not_run(*_):
        raise AssertionError("a valid cache must suppress automatic audit")

    monkeypatch.setattr(bootstrap, "run_investigation", must_not_run)
    with TestClient(app) as client:
        health = client.get("/v1/decision/health")
        evaluation = client.post(
            "/v1/decision/evaluate", json=default_request().model_dump(mode="json")
        )

    assert health.json()["audit_status"] == "completed"
    assert evaluation.json()["audit_status"] == "completed"


def test_auto_audit_is_nonblocking_and_shutdown_cancels_cleanup(monkeypatch, tmp_path):
    from decision import bootstrap
    from decision.app import app

    _configure_runtime(monkeypatch, tmp_path, audit_mode="auto")
    monkeypatch.setattr(bootstrap, "load_investigation", lambda *_: None)
    started = threading.Event()
    cleaned = threading.Event()

    async def long_audit(*_, **_kwargs):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    monkeypatch.setattr(bootstrap, "run_investigation", long_audit)
    with TestClient(app) as client:
        response = client.get("/v1/decision/health")
        assert response.status_code == 200
        assert response.json()["audit_status"] == "running"
        assert started.wait(timeout=1)

    assert cleaned.wait(timeout=1)


def test_auto_audit_failure_does_not_make_decisions_not_ready(monkeypatch, tmp_path):
    from decision import bootstrap
    from decision.app import app

    _configure_runtime(monkeypatch, tmp_path, audit_mode="auto")
    monkeypatch.setattr(bootstrap, "load_investigation", lambda *_: None)
    attempted = threading.Event()

    async def failed_audit(*_, **_kwargs):
        attempted.set()
        raise RuntimeError("fixture MCP failure")

    monkeypatch.setattr(bootstrap, "run_investigation", failed_audit)
    with TestClient(app) as client:
        assert attempted.wait(timeout=1)
        health = client.get("/v1/decision/health")
        evaluation = client.post(
            "/v1/decision/evaluate", json=default_request().model_dump(mode="json")
        )

    assert health.status_code == evaluation.status_code == 200
    assert health.json()["audit_status"] == "failed"
    assert evaluation.json()["audit_status"] == "failed"


@pytest.mark.asyncio
async def test_auto_audit_has_a_120_second_wall_clock_budget(monkeypatch, tmp_path):
    from decision import bootstrap

    expected_snapshot = golden_snapshot()
    paths = RuntimePaths(data_dir=tmp_path / "data", output_dir=tmp_path / "out")
    completed = _completed_audit(expected_snapshot.dataset_id)
    observed: list[int] = []

    async def audit(*_, snapshot):
        assert snapshot is expected_snapshot
        return completed

    async def capture_budget(awaitable, *, timeout):
        observed.append(timeout)
        return await awaitable

    monkeypatch.setattr(bootstrap, "run_investigation", audit)
    monkeypatch.setattr(bootstrap.asyncio, "wait_for", capture_budget)
    app = SimpleNamespace(state=SimpleNamespace())

    await bootstrap._run_audit(app, paths, expected_snapshot)

    assert observed == [120]
    assert app.state.decision_audit_status == "completed"


@pytest.mark.asyncio
async def test_investigation_reuses_snapshot_and_does_not_block_event_loop(monkeypatch, tmp_path):
    from decision import investigation

    snapshot = golden_snapshot()
    cached = _completed_audit(snapshot.dataset_id)

    def must_not_reload(_):
        raise AssertionError("the lifecycle snapshot must be reused")

    def slow_cache_read(*_):
        time.sleep(0.15)
        return cached

    monkeypatch.setattr(investigation, "load_snapshot", must_not_reload)
    monkeypatch.setattr(investigation, "load_audit", slow_cache_read)
    started = asyncio.get_running_loop().time()
    task = asyncio.create_task(
        investigation.run_investigation(
            tmp_path / "data", tmp_path / "out", snapshot=snapshot
        )
    )

    await asyncio.sleep(0.02)
    elapsed = asyncio.get_running_loop().time() - started
    result = await task

    assert elapsed < 0.08
    assert result == cached


def test_malformed_cache_does_not_abort_healthy_lifespan(monkeypatch, tmp_path):
    from decision.app import app

    snapshot, paths, _ = _configure_runtime(monkeypatch, tmp_path, audit_mode="off")
    path = audit_path(paths.output_dir, snapshot.dataset_id)
    path.parent.mkdir(parents=True)
    path.write_text("[]")

    with TestClient(app) as client:
        health = client.get("/v1/decision/health")

    assert health.status_code == 200
    assert health.json()["dataset_id"] == snapshot.dataset_id


def test_compose_readiness_checks_both_health_routes_before_dashboard_starts():
    compose_path = Path(__file__).parents[2] / "docker-compose.yml"
    compose = yaml.safe_load(compose_path.read_text())

    health_command = compose["services"]["api"]["healthcheck"]["test"][-1]
    assert "http://localhost:8000/health" in health_command
    assert "http://localhost:8000/v1/decision/health" in health_command
    assert compose["services"]["dashboard"]["depends_on"]["api"]["condition"] == "service_healthy"


def test_latest_matching_audit_updates_reads_without_changing_evaluation_id(monkeypatch, tmp_path):
    from decision import bootstrap
    from decision.app import app

    snapshot, paths, _ = _configure_runtime(monkeypatch, tmp_path, audit_mode="off")
    with TestClient(app) as client:
        initial = client.post(
            "/v1/decision/evaluate", json=default_request().model_dump(mode="json")
        )
        save_audit(paths.output_dir, _completed_audit(snapshot.dataset_id))
        refreshed = client.post(
            "/v1/decision/evaluate", json=default_request().model_dump(mode="json")
        )
        investigation = client.get(
            "/v1/decision/investigations/node_recommendation_audit",
            params={"dataset_id": snapshot.dataset_id},
        )

    assert initial.json()["audit_status"] == "not_run"
    assert refreshed.json()["audit_status"] == "completed"
    assert initial.json()["meta"]["evaluation_id"] == refreshed.json()["meta"]["evaluation_id"]
    assert investigation.json()["investigation"]["status"] == "completed"


def test_evaluation_cache_is_lru_bounded_and_returns_isolated_results(monkeypatch, tmp_path):
    from decision import bootstrap, routes
    from decision.app import app

    _configure_runtime(monkeypatch, tmp_path, audit_mode="off")
    monkeypatch.setattr(bootstrap, "load_investigation", lambda *_: None)
    real_evaluate = routes.run_evaluate
    calls = 0

    def counted_evaluate(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real_evaluate(*args, **kwargs)

    monkeypatch.setattr(routes, "run_evaluate", counted_evaluate)
    payload = default_request().model_dump(mode="json")
    with TestClient(app) as client:
        payload["pricing"]["usd_per_gpu_hour"] = 1.0
        first_a = client.post("/v1/decision/evaluate", json=payload).json()
        payload["pricing"]["usd_per_gpu_hour"] = 2.0
        client.post("/v1/decision/evaluate", json=payload)
        payload["pricing"]["usd_per_gpu_hour"] = 1.0
        second_a = client.post("/v1/decision/evaluate", json=payload).json()
        assert calls == 2
        assert first_a == second_a

        for price in range(3, 67):
            payload["pricing"]["usd_per_gpu_hour"] = float(price)
            client.post("/v1/decision/evaluate", json=payload)
        assert len(app.state.decision_evaluation_cache) == 64
        payload["pricing"]["usd_per_gpu_hour"] = 1.0
        client.post("/v1/decision/evaluate", json=payload)

    assert calls == 67


def test_evaluation_cache_uses_evaluation_identity_and_deep_copies(monkeypatch, tmp_path):
    from decision import bootstrap, routes
    from decision.app import app

    snapshot, _, _ = _configure_runtime(monkeypatch, tmp_path, audit_mode="off")
    monkeypatch.setattr(bootstrap, "load_investigation", lambda *_: None)
    real_evaluate = routes.run_evaluate
    calls = 0

    def counted_evaluate(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real_evaluate(*args, **kwargs)

    monkeypatch.setattr(routes, "run_evaluate", counted_evaluate)
    positive_zero = default_request().model_dump(mode="json")
    negative_zero = default_request().model_dump(mode="json")
    positive_zero["pricing"]["usd_per_gpu_hour"] = 0.0
    negative_zero["pricing"]["usd_per_gpu_hour"] = -0.0

    with TestClient(app) as client:
        first = client.post("/v1/decision/evaluate", json=positive_zero).json()
        second = client.post("/v1/decision/evaluate", json=negative_zero).json()

    assert calls == 1
    assert first["meta"]["evaluation_id"] == second["meta"]["evaluation_id"]

    cache = bootstrap.EvaluationCache(maxsize=1)
    source = real_evaluate(snapshot, default_request())
    first_object = cache.get_or_create("same", lambda: source)
    first_object.warnings.append("mutated top level")
    first_object.actions[0].warnings.append("mutated nested value")
    second_object = cache.get_or_create("same", lambda: source)

    assert second_object is not first_object
    assert second_object.warnings == []
    assert second_object.actions[0].warnings == []


def test_openapi_import_does_not_read_data_or_start_audit(tmp_path):
    env = {
        **os.environ,
        "PYTHONPATH": "track-2",
        "MGAI_DATA_DIR": str(tmp_path / "missing"),
        "TRACK2_DATA_DIR": str(tmp_path / "missing"),
        "TRACK2_OUTPUT_DIR": str(tmp_path / "out"),
        "TRACK2_AUDIT_MODE": "auto",
    }
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from decision.app import app; print(app.openapi()['info']['title'])",
        ],
        cwd=Path(__file__).parents[2],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "MGAI API (hackathon facsimile)"
    assert not (tmp_path / "out").exists()
