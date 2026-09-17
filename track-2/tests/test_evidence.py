import pytest
import numpy as np
import pandas as pd

from decision.errors import DecisionError
from decision.service import evidence_page, finding_detail, job_detail
from factories import default_request, golden_snapshot
from analysis_fixtures import clone_snapshot


def test_marginal_evidence_keeps_overlap_with_zero_contribution():
    request = default_request().model_copy(update={"selected_action_ids": ["cpu_migration", "idle_session_reclaim"]})
    page = evidence_page(golden_snapshot(), request, "idle_session_reclaim", "marginal", 0, 1)
    assert page.total == 2 and page.next_offset == 1
    assert page.rows[0].job_id == "102"
    assert page.rows[0].eligibility == "overlap_assigned_elsewhere"
    assert page.rows[0].contribution_gpu_hours.point == 0


def test_details_preserve_gpu_rows_and_finding_links():
    snapshot = golden_snapshot()
    assert len(job_detail(snapshot, "102").gpus) == 2
    assert finding_detail(snapshot, "finding-102").job_ids == ["102"]
    with pytest.raises(DecisionError) as error:
        job_detail(snapshot, "999")
    assert error.value.code == "NOT_FOUND"


@pytest.mark.parametrize("source,expected", [
    (np.array(["node-b", "node-a"]), ["node-b", "node-a"]),
    (np.array(["node-a"]), ["node-a"]),
    (np.array([], dtype=str), []),
    (["node-b", "node-a"], ["node-b", "node-a"]),
    ([], []),
    (None, []),
    (float("nan"), []),
    (pd.NA, []),
])
def test_job_detail_preserves_array_list_and_null_node_failure_nodes(source, expected):
    snapshot = golden_snapshot()
    jobs = snapshot.jobs.copy()
    jobs["nodefail_nodes"] = pd.Series([source, None, None], dtype=object)
    jobs["nodefail_exact"] = True
    jobs["hit_node_failure"] = True
    detail = job_detail(clone_snapshot(snapshot, jobs=jobs), "101")
    assert detail.nodefail_nodes == expected
    assert detail.nodefail_exact is True
    assert detail.hit_node_failure is True
