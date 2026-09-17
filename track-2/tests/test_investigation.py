from decision.investigation import decide_node, failed_investigation
from decision.contracts import ToolCallRecord


def test_empty_chain_is_not_a_healthy_verdict():
    node = decide_node(
        node_name="fixture-node", resource_id="fixture-resource",
        findings=[], causal_results=[{"findings": [], "message": "No causal chain"}],
        reported_findings=1, returned_findings=1, truncated=False,
        scope_description="fixture episode", corroboration=None,
    )
    assert node.cause == "cannot_determine"
    assert node.verdict == "cannot_determine"


def test_user_code_chain_prevents_drain():
    node = decide_node(
        node_name="n1", resource_id="node-1",
        findings=[{"id": "f1", "metadata": {}}],
        causal_results=[{"findings": [{"culprit": [{"resource_id": "ns-u1", "type": "k8s:namespace"}], "causal_chain": [{"pattern": "concentrated_in_one_person"}]}]}],
        reported_findings=1, returned_findings=1, truncated=False,
        scope_description="sample window", corroboration={"jobs": 3, "users": 1},
    )
    assert node.cause == "user_code"
    assert node.verdict == "no_drain"


def test_failed_health_has_failed_status():
    receipt = ToolCallRecord(call_id="c1", sequence=1, tool_name="health", arguments={},
        started_at_utc="2026-01-01T00:00:00Z", duration_ms=1, status="error",
        result=None, error="boom")
    result = failed_investigation("dataset", receipt)
    assert result.status == "failed"
    assert result.verdict == "cannot_determine"
    assert result.nodes == []
