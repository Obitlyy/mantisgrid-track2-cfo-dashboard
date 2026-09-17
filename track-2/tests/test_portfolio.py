from decision.service import evaluate
from factories import default_request, golden_snapshot


def test_portfolio_assigns_whole_overlap_to_cpu():
    request = default_request().model_copy(update={"selected_action_ids": ["idle_session_reclaim", "cpu_migration"]})
    result = evaluate(golden_snapshot(), request)
    assert result.request.selected_action_ids == ["cpu_migration", "idle_session_reclaim"]
    assert result.portfolio.recoverable_gpu_hours.point == 17
    assert result.portfolio.overlap_jobs == 1
    assert sum(action.standalone_recoverable_gpu_hours.point for action in result.actions) == 20
