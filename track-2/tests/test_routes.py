from fastapi import FastAPI
from fastapi.testclient import TestClient

from decision.routes import get_chat_client, get_snapshot, router
from factories import default_request, golden_snapshot


def client():
    app = FastAPI()
    app.include_router(router, prefix="/v1/decision")
    app.dependency_overrides[get_snapshot] = golden_snapshot
    return TestClient(app)


def test_evaluate_and_dataset_mismatch_error_shape():
    with client() as http:
        response = http.post("/v1/decision/evaluate", json=default_request().model_dump(mode="json"))
        assert response.status_code == 200
        dataset_id = response.json()["meta"]["dataset_id"]
        mismatch = http.get("/v1/decision/jobs/102", params={"dataset_id": dataset_id + "x"})
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "DATASET_MISMATCH"


def test_invalid_request_uses_project_error_shape():
    payload = default_request().model_dump(mode="json")
    payload["pricing"]["usd_per_gpu_hour"] = True
    with client() as http:
        response = http.post("/v1/decision/evaluate", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_job_route_returns_array_valued_node_failure_nodes():
    import numpy as np
    import pandas as pd
    from analysis_fixtures import clone_snapshot
    snapshot = golden_snapshot()
    jobs = snapshot.jobs.copy()
    jobs["nodefail_nodes"] = pd.Series([np.array(["node-b", "node-a"]), None, None], dtype=object)
    snapshot = clone_snapshot(snapshot, jobs=jobs)
    with client() as http:
        http.app.dependency_overrides[get_snapshot] = lambda: snapshot
        response = http.get("/v1/decision/jobs/101", params={"dataset_id": snapshot.dataset_id})
    assert response.status_code == 200
    assert response.json()["nodefail_nodes"] == ["node-b", "node-a"]


def test_chat_route_uses_applied_scenario_and_returns_receipts():
    class FakeChatClient:
        model = "deepseek-fixture"
        def complete(self, messages, tools):
            return {
                "choices": [{"message": {"role": "assistant", "content": "Use the CPU migration pilot first."}}],
                "model": self.model,
                "usage": {"prompt_tokens": 4, "completion_tokens": 6, "total_tokens": 10},
            }

    snapshot = golden_snapshot()
    http = client()
    http.app.dependency_overrides[get_chat_client] = FakeChatClient
    body = {
        "message": "What should we do first?",
        "dataset_id": snapshot.dataset_id,
        "evaluation_request": default_request().model_dump(mode="json"),
        "history": [],
    }
    with http:
        response = http.post("/v1/decision/chat", json=body)
    assert response.status_code == 200
    assert response.json()["answer"] == "Use the CPU migration pilot first."
    assert response.json()["meta"]["dataset_id"] == snapshot.dataset_id
    assert response.json()["usage"]["total_tokens"] == 10
