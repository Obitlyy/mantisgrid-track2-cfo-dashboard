import json

from decision.audit_storage import audit_lock, load_audit, save_audit
from decision.investigation import not_run_investigation


def test_cache_round_trip_and_dataset_validation(tmp_path):
    inv = not_run_investigation("dataset-a")
    path = save_audit(tmp_path, inv)
    assert path.name == "node_recommendation_audit.json"
    assert load_audit(tmp_path, "dataset-a") == inv
    assert load_audit(tmp_path, "dataset-b") is None


def test_corrupt_or_incompatible_cache_is_ignored(tmp_path):
    inv = not_run_investigation("dataset-a")
    path = save_audit(tmp_path, inv)
    payload = json.loads(path.read_text())
    payload["schema_version"] = "2.0.0"
    path.write_text(json.dumps(payload))
    assert load_audit(tmp_path, "dataset-a") is None
    path.write_text("{")
    assert load_audit(tmp_path, "dataset-a") is None
    path.write_text("[]")
    assert load_audit(tmp_path, "dataset-a") is None


def test_lock_is_non_blocking(tmp_path):
    with audit_lock(tmp_path, "dataset-a") as first:
        assert first is True
        with audit_lock(tmp_path, "dataset-a") as second:
            assert second is False
