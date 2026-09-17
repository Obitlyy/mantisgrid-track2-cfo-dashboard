from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError


def test_contract_numeric_and_bounds_validation():
    from decision.contracts import Bounds, Pricing

    for value in (True, "2.5", float("nan"), float("inf"), -1):
        with pytest.raises(ValidationError):
            Pricing(usd_per_gpu_hour=value, usd_per_cpu_core_hour=None)
    with pytest.raises(ValidationError):
        Bounds(low=2, point=1, high=3)
    assert Pricing(usd_per_gpu_hour=0, usd_per_cpu_core_hour=None).usd_per_gpu_hour == 0


def test_resolve_paths_rejects_disagreement(monkeypatch, tmp_path):
    from decision.config import resolve_paths

    monkeypatch.setenv("MGAI_DATA_DIR", str(tmp_path / "a"))
    monkeypatch.setenv("TRACK2_DATA_DIR", str(tmp_path / "b"))
    with pytest.raises(ValueError, match="same directory"):
        resolve_paths()


def test_reuse_preflights_all_conflicts(tmp_path):
    from scripts.reuse_data import reuse_data

    source, destination = tmp_path / "source", tmp_path / "destination"
    rels = [Path("raw/dcgm.csv"), Path("raw/scheduler_data.csv")]
    for rel in rels:
        (source / rel).parent.mkdir(parents=True, exist_ok=True)
        (source / rel).write_text(rel.name)
    (destination / rels[0]).parent.mkdir(parents=True)
    (destination / rels[0]).write_text("conflict")
    with pytest.raises(ValueError, match="conflict"):
        reuse_data(source, destination, rels)
    assert not (destination / rels[1]).exists()


def test_snapshot_dataset_id_uses_value_digests(monkeypatch, tmp_path):
    from decision import data as module

    files = module.OFFICIAL_FILES
    expected = {name: hashlib.sha256(name.encode()).hexdigest() for name in files}
    monkeypatch.setattr(module, "_expected_digests", lambda: expected)
    monkeypatch.setattr(module, "official_digest", lambda path: expected[str(path.relative_to(tmp_path))])
    jobs = pd.DataFrame([{
        "id_job": 101, "id_user": 1, "state_name": "COMPLETED", "gpu_count": 1,
        "gpu_hours": 1.0, "sm_util_avg": 0.0, "sm_util_max": 0.0,
        "time_submit": 0.0, "time_end": 10.0,
    }])
    gpus = pd.DataFrame([{"Node": "n1", "gpu_id": 0, "id_job": 101}])
    resources = pd.DataFrame([{"id": "r1"}])
    edges = pd.DataFrame([{"sourceId": "r1", "destinationId": "r1"}])
    frames = {
        "jobs.parquet": jobs, "gpus.parquet": gpus,
        "resources.parquet": resources, "edges.parquet": edges,
    }
    monkeypatch.setattr(pd, "read_parquet", lambda path: frames[path.name])
    monkeypatch.setattr(Path, "read_text", lambda self, **kwargs: "[]" if self.name == "findings.json" else "")
    for name in files:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    snapshot = module.load_snapshot(tmp_path)
    payload = "".join(f"{name} {expected[name]}\n" for name in files).encode()
    assert snapshot.dataset_id == hashlib.sha256(payload).hexdigest()
    assert snapshot.data_origin == "official_dataset"


def test_decision_routes_are_typed_not_ready():
    from fastapi.testclient import TestClient
    from decision.app import app

    with TestClient(app) as client:
        response = client.post("/v1/decision/evaluate", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
