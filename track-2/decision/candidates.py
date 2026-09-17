from dataclasses import dataclass
import math
import pandas as pd
import numpy as np

from decision.errors import DecisionError
from decision.data import validate_evidence_ids

@dataclass(frozen=True)
class CandidateLedger:
    rows: pd.DataFrame
    finding_index: dict[str, dict]

COLS = ["action_id", "job_id", "user_id", "state_name", "gpu_count", "measured_gpu_hours",
        "capped_gpu_hours", "candidate_gpu_hours", "eligible", "exclusion_reasons", "quality_flags",
        "finding_ids", "nodes"]


def _sid(value, *, required=False):
    if value is None or (isinstance(value, float) and math.isnan(value)): return None
    if isinstance(value, float):
        if not value.is_integer() or abs(value) > 2**53:
            if required: raise DecisionError("DATA_INVALID", "Unsafe source identifier.", {"field": "id_job"}, 503)
            return None
        value = int(value)
    text = str(value)
    return text[:-2] if text.endswith(".0") and text[:-2].lstrip("-").isdigit() else text


def _finding_jobs(finding, resources):
    jobs = set()
    md = finding.get("metadata") or {}
    if "job_id" in md: jobs.add(_sid(md["job_id"], required=True))
    if len(resources):
        for rid in finding.get("resourceIds", []):
            match = resources[resources.get("id", pd.Series(dtype=object)).astype(str) == str(rid)]
            for value in match.get("resourceId", []):
                if value is not None: jobs.add(_sid(value, required=True))
    return jobs


def build_candidates(snapshot):
    jobs, gpus = snapshot.jobs, snapshot.gpus
    validate_evidence_ids(snapshot.resources, snapshot.findings)
    if jobs["id_job"].duplicated().any() or gpus.duplicated(["Node", "gpu_id", "id_job"]).any():
        raise DecisionError("DATA_INVALID", "Duplicate source key.", {}, 503)
    index = {}
    gpu_job_ids = gpus["id_job"].map(lambda x: _sid(x, required=True))
    gpu_groups = {job_id: gpus.loc[indexes] for job_id, indexes in gpu_job_ids.groupby(gpu_job_ids).groups.items()}
    matches = {"cpu_migration": {}, "idle_session_reclaim": {}}
    detectors = {"rules::gpu-not-needed": "cpu_migration", "rules::idle-interactive-session": "idle_session_reclaim", "rules::slow-cancel-of-idle-job": "idle_session_reclaim"}
    for finding in snapshot.findings:
        fid = str(finding.get("id"))
        index[fid] = finding
        action = detectors.get(finding.get("detectorId"))
        if action:
            for jid in _finding_jobs(finding, snapshot.resources): matches[action].setdefault(jid, []).append(fid)
    rows = []
    for job in jobs.to_dict("records"):
        jid = _sid(job.get("id_job"), required=True)
        state, kind = str(job.get("state_name") or "UNKNOWN"), str(job.get("job_type") or "")
        mean, peak = job.get("sm_util_avg"), job.get("sm_util_max")
        hours, wall = job.get("gpu_hours"), job.get("walltime_sec")
        cpu_pred = state == "COMPLETED" and mean == 0 and peak == 0 and float(hours) > 1
        idle_pred = (kind == "LLSUB:INTERACTIVE" or state == "CANCELLED") and float(wall) > 14400 and float(mean) < 5
        for fid in matches["idle_session_reclaim"].get(jid, []):
            detector = index[fid]["detectorId"]
            specific = kind == "LLSUB:INTERACTIVE" if detector == "rules::idle-interactive-session" else state == "CANCELLED"
            if not specific or not idle_pred:
                raise DecisionError("DATA_INVALID", "Detector predicate and finding disagree.", {"detector_id": detector, "job_id": jid}, 503)
        for action, pred in (("cpu_migration", cpu_pred), ("idle_session_reclaim", idle_pred)):
            fids = matches[action].get(jid, [])
            if bool(fids) != bool(pred):
                raise DecisionError("DATA_INVALID", "Candidate predicate and finding disagree.", {"action_id": action, "job_id": jid}, 503)
            if not pred: continue
            reasons, flags = [], []
            try: gpu_count = int(job.get("gpu_count"))
            except Exception: gpu_count = 0
            if job.get("attempts") != 1: reasons.append("REQUEUED_JOB")
            if not isinstance(wall, (int, float)) or not np.isfinite(wall) or wall <= 0: reasons.append("INVALID_WALLTIME")
            cards = gpu_groups.get(jid, gpus.iloc[0:0])
            if cards.empty: reasons.append("MISSING_GPU_ROWS")
            elif len(cards) != gpu_count: reasons.append("GPU_COUNT_MISMATCH")
            caps = []
            nodes = sorted(set(cards.get("Node", pd.Series(dtype=str)).dropna().astype(str)))
            for card in cards.to_dict("records"):
                duration = card.get("totalexecutiontime_sec")
                avg, maximum = card.get("smutilization_pct_avg"), card.get("smutilization_pct_max")
                if not isinstance(duration, (int, float)) or not np.isfinite(duration) or duration < 0:
                    reasons.append("INVALID_GPU_DURATION"); continue
                if not all(isinstance(v, (int, float)) and np.isfinite(v) and 0 <= v <= 100 for v in (avg, maximum)):
                    reasons.append("INVALID_GPU_UTILIZATION")
                if np.isfinite(wall) and duration > wall: flags.append("DURATION_CAPPED")
                if np.isfinite(wall): caps.append(min(float(duration), float(wall)) / 3600)
                if action == "cpu_migration" and ((avg or 0) != 0 or (maximum or 0) != 0): reasons.append("CONTRADICTORY_ZERO_UTILIZATION")
            reasons = sorted(set(reasons)); flags = sorted(set(flags))
            capped = float(sum(caps)) if caps and not any(r in reasons for r in ("MISSING_GPU_ROWS", "INVALID_GPU_DURATION")) else None
            candidate = None if capped is None else (capped if action == "cpu_migration" else min(capped, gpu_count * max(float(wall) / 3600 - 4, 0)))
            user = _sid(job.get("id_user"))
            if user is None and job.get("id_user") is not None: flags.append("UNSAFE_SOURCE_IDENTIFIER")
            rows.append(dict(action_id=action, job_id=jid, user_id=user, state_name=state, gpu_count=gpu_count,
                             measured_gpu_hours=float(hours), capped_gpu_hours=capped, candidate_gpu_hours=candidate,
                             eligible=not reasons, exclusion_reasons=reasons, quality_flags=sorted(set(flags)),
                             finding_ids=sorted(set(fids)), nodes=nodes))
    return CandidateLedger(pd.DataFrame(rows, columns=COLS), index)
