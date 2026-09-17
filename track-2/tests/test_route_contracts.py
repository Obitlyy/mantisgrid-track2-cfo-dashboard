from fastapi.testclient import TestClient

from decision.app import app


def test_health_is_honestly_not_ready_when_lifespan_cannot_load(monkeypatch, tmp_path):
    from decision import bootstrap
    from decision.errors import DecisionError

    monkeypatch.setattr(
        bootstrap,
        "resolve_paths",
        lambda: __import__("decision.config", fromlist=["RuntimePaths"]).RuntimePaths(
            tmp_path, tmp_path / "out"
        ),
    )
    monkeypatch.setattr(
        bootstrap,
        "load_snapshot",
        lambda _: (_ for _ in ()).throw(
            DecisionError("DATA_NOT_READY", "missing", {}, 503)
        ),
    )
    with TestClient(app) as client:
        response = client.get("/v1/decision/health")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert not any(getattr(route, "path", "").startswith("/decision-api") for route in app.routes)
