import pytest
from decision.data import load_snapshot
from decision.errors import DecisionError

def test_missing_snapshot_is_typed_not_ready(tmp_path):
    with pytest.raises(DecisionError) as caught: load_snapshot(tmp_path)
    assert caught.value.code=='DATA_NOT_READY' and caught.value.http_status==503


@pytest.mark.parametrize("kind", ["resource", "finding"])
def test_snapshot_loader_rejects_duplicate_evidence_ids(tmp_path, monkeypatch, kind):
    import json
    import pandas as pd
    from decision import data
    from factories import golden_snapshot
    snapshot = golden_snapshot()
    frames = [snapshot.jobs, snapshot.gpus, pd.DataFrame([{"id": "r1"}, {"id": "r1" if kind == "resource" else "r2"}]), pd.DataFrame()]
    for name, frame in zip(data.OFFICIAL_FILES, frames):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(target)
    findings = [{"id": "f1"}, {"id": "f1" if kind == "finding" else "f2"}]
    (tmp_path / data.OFFICIAL_FILES[-1]).write_text(json.dumps(findings))
    monkeypatch.setattr(data, "_expected_digests", lambda: {name: data.official_digest(tmp_path / name) for name in data.OFFICIAL_FILES})
    with pytest.raises(DecisionError, match="keys"):
        load_snapshot(tmp_path)
