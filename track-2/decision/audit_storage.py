from __future__ import annotations

import contextlib
import fcntl
import json
import logging
import os
import tempfile
from pathlib import Path

from decision.contracts import Investigation

LOG = logging.getLogger(__name__)
SCHEMA_VERSION = "1.0.0"
ANALYSIS_VERSION = "track2-decision-v1"


def audit_path(output_dir: Path, dataset_id: str) -> Path:
    return Path(output_dir) / "mcp" / dataset_id / "node_recommendation_audit.json"


def save_audit(output_dir: Path, investigation: Investigation) -> Path:
    path = audit_path(output_dir, investigation.dataset_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    envelope = {"schema_version": SCHEMA_VERSION, "analysis_version": ANALYSIS_VERSION,
                "dataset_id": investigation.dataset_id,
                "investigation": investigation.model_dump(mode="json")}
    fd, temporary = tempfile.mkstemp(prefix=".audit-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(envelope, stream, ensure_ascii=False, allow_nan=False)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    return path


def load_audit(output_dir: Path, dataset_id: str) -> Investigation | None:
    path = audit_path(output_dir, dataset_id)
    try:
        payload = json.loads(path.read_text())
        if not isinstance(payload, dict):
            return None
        if payload.get("schema_version") != SCHEMA_VERSION or payload.get("analysis_version") != ANALYSIS_VERSION:
            return None
        if payload.get("dataset_id") != dataset_id:
            return None
        value = Investigation.model_validate(payload["investigation"])
        return value if value.dataset_id == dataset_id else None
    except (OSError, ValueError, KeyError, TypeError) as exc:
        LOG.info("Ignoring invalid audit cache %s: %s", path, exc)
        return None


@contextlib.contextmanager
def audit_lock(output_dir: Path, dataset_id: str):
    directory = audit_path(output_dir, dataset_id).parent
    directory.mkdir(parents=True, exist_ok=True)
    stream = (directory / ".audit.lock").open("a+")
    acquired = False
    try:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError:
            pass
        yield acquired
    finally:
        if acquired: fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()
