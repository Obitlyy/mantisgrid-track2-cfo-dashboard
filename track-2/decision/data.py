from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from api.main import DEFAULT_PRICE_BOOK
from decision.contracts import SampleWindow
from decision.errors import DecisionError
from scripts.checksum_data import digest as official_digest

OFFICIAL_FILES = ["prepped/jobs.parquet", "prepped/gpus.parquet", "synthetic/resources.parquet", "synthetic/edges.parquet", "synthetic/findings.json"]
MANIFEST = Path(__file__).resolve().parents[1] / "contracts" / "official-checksums.txt"


@dataclass(frozen=True)
class DataSnapshot:
    dataset_id: str
    jobs: pd.DataFrame
    gpus: pd.DataFrame
    resources: pd.DataFrame
    edges: pd.DataFrame
    findings: list[dict]
    sample_window: SampleWindow
    data_origin: str


def _expected_digests() -> dict[str, str]:
    result = {}
    for line in MANIFEST.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            value, name = line.split()
            result[name] = value
    return result


def _fail(code: str, message: str, details: dict) -> None:
    raise DecisionError(code, message, details, 503)


def validate_evidence_ids(resources: pd.DataFrame, findings: list[dict]) -> None:
    """Reject ambiguous evidence keys before building any lookup index."""
    sources = [("Resource", resources.get("id", pd.Series(dtype=object)), len(resources)),
               ("Finding", pd.Series([f.get("id") for f in findings], dtype=object), len(findings))]
    for name, ids, count in sources:
        if len(ids) != count or ids.isna().any() or ids.astype(str).str.strip().eq("").any() or ids.astype(str).duplicated().any():
            _fail("DATA_INVALID", f"{name} primary keys are invalid or duplicated.", {"source": name.lower()})


def load_snapshot(data_dir: Path) -> DataSnapshot:
    data_dir = Path(data_dir).resolve()
    missing = [name for name in OFFICIAL_FILES if not (data_dir / name).is_file()]
    if missing:
        _fail("DATA_NOT_READY", "Official data files are missing.", {"missing": missing})
    expected = _expected_digests()
    actual = {name: official_digest(data_dir / name) for name in OFFICIAL_FILES}
    mismatches = [name for name in OFFICIAL_FILES if actual[name] != expected.get(name)]
    if mismatches:
        _fail("DATA_INVALID", "Official data checksums do not match.", {"files": mismatches})
    jobs = pd.read_parquet(data_dir / OFFICIAL_FILES[0])
    gpus = pd.read_parquet(data_dir / OFFICIAL_FILES[1])
    resources = pd.read_parquet(data_dir / OFFICIAL_FILES[2])
    edges = pd.read_parquet(data_dir / OFFICIAL_FILES[3])
    findings = json.loads((data_dir / OFFICIAL_FILES[4]).read_text())
    validate_evidence_ids(resources, findings)
    required_jobs = {"id_job", "state_name", "gpu_count", "gpu_hours", "sm_util_avg", "sm_util_max", "time_submit", "time_end"}
    required_gpus = {"Node", "gpu_id", "id_job"}
    missing_columns = sorted(required_jobs - set(jobs.columns) | required_gpus - set(gpus.columns))
    if missing_columns:
        _fail("DATA_INVALID", "Required columns are missing.", {"columns": missing_columns})
    if jobs["id_job"].isna().any() or jobs["id_job"].duplicated().any():
        _fail("DATA_INVALID", "Job primary keys are invalid.", {"count": int(jobs["id_job"].isna().sum() + jobs["id_job"].duplicated().sum())})
    if gpus.duplicated(["Node", "gpu_id", "id_job"]).any():
        _fail("DATA_INVALID", "GPU physical keys are duplicated.", {"count": int(gpus.duplicated(["Node", "gpu_id", "id_job"]).sum())})
    util = pd.to_numeric(jobs["sm_util_avg"], errors="coerce")
    if not np.isfinite(util).all():
        _fail("DATA_INVALID", "Baseline utilization is missing or non-finite.", {"field": "sm_util_avg", "count": int((~np.isfinite(util)).sum())})
    start, end = float(jobs.time_submit.min()), float(jobs.time_end.max())
    epoch = int(DEFAULT_PRICE_BOOK.epoch_offset)
    mapped = lambda value: dt.datetime.fromtimestamp(value + epoch, dt.timezone.utc).isoformat()
    window = SampleWindow(start_offset_sec=start, end_offset_sec=end, epoch_offset_sec=epoch, mapped_start_utc=mapped(start), mapped_end_utc=mapped(end))
    stream = "".join(f"{name} {actual[name]}\n" for name in OFFICIAL_FILES).encode("utf-8")
    return DataSnapshot(hashlib.sha256(stream).hexdigest(), jobs, gpus, resources, edges, findings, window, "official_dataset")
