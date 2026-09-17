from analysis_fixtures import clone_snapshot
from decision.candidates import build_candidates
from factories import golden_snapshot
import pytest
from decision.errors import DecisionError


def test_candidate_caps_and_detector_union():
    rows = build_candidates(golden_snapshot()).rows.set_index(["action_id", "job_id"])
    assert rows.index.is_unique
    assert rows.loc[("cpu_migration", "102"), "candidate_gpu_hours"] == 20
    assert rows.loc[("idle_session_reclaim", "102"), "candidate_gpu_hours"] == 12
    assert rows.loc[("idle_session_reclaim", "103"), "candidate_gpu_hours"] == 8


def test_requeued_candidate_is_retained_but_excluded():
    snapshot = golden_snapshot()
    jobs = snapshot.jobs.copy()
    jobs.loc[jobs.id_job == 101, "attempts"] = 2
    row = build_candidates(clone_snapshot(snapshot, jobs=jobs)).rows.query("job_id == '101'").iloc[0]
    assert not bool(row.eligible)
    assert "REQUEUED_JOB" in row.exclusion_reasons


@pytest.mark.parametrize("job,detector", [(102, "rules::slow-cancel-of-idle-job"), (103, "rules::idle-interactive-session")])
def test_idle_requires_the_matching_detector_predicate(job, detector):
    snapshot = golden_snapshot()
    jobs = snapshot.jobs.copy()
    if job == 103:
        jobs.loc[jobs.id_job == job, "job_type"] = "batch"
    findings = [dict(f, detectorId=detector) if f["metadata"]["job_id"] == job and "gpu-not-needed" not in f["detectorId"] else f for f in snapshot.findings]
    with pytest.raises(DecisionError, match="predicate"):
        build_candidates(clone_snapshot(snapshot, jobs=jobs, findings=findings))


def test_duplicate_finding_ids_fail_instead_of_retaining_first():
    snapshot = golden_snapshot()
    with pytest.raises(DecisionError, match="Finding"):
        build_candidates(clone_snapshot(snapshot, findings=snapshot.findings + [snapshot.findings[0]]))


@pytest.mark.parametrize("job_type", ["NONINTERACTIVE", "LLSUB:NONINTERACTIVE", "INTERACTIVE"])
@pytest.mark.parametrize("has_idle_finding", [False, True])
def test_interactive_predicate_requires_exact_canonical_job_type(job_type, has_idle_finding):
    snapshot = golden_snapshot()
    jobs = snapshot.jobs.copy()
    jobs.loc[jobs.id_job == 102, "job_type"] = job_type
    findings = snapshot.findings if has_idle_finding else [f for f in snapshot.findings if f["id"] != "finding-102-idle"]
    changed = clone_snapshot(snapshot, jobs=jobs, findings=findings)
    if has_idle_finding:
        with pytest.raises(DecisionError, match="predicate"):
            build_candidates(changed)
    else:
        rows = build_candidates(changed).rows
        assert rows[(rows.action_id == "idle_session_reclaim") & (rows.job_id == "102")].empty
