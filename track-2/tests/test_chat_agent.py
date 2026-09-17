import pytest

from decision.chat_agent import run_chat
from decision.contracts import ChatRequest
from decision.deepseek_client import DeepSeekClient
from decision.errors import DecisionError
from decision.investigation import not_run_investigation
from factories import default_request, golden_snapshot


class FakeClient:
    model = "deepseek-fixture"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, messages, tools):
        self.calls.append({"messages": messages, "tools": tools})
        return self.responses.pop(0)


def payload(message="What should we do first?"):
    snapshot = golden_snapshot()
    return ChatRequest(
        message=message,
        dataset_id=snapshot.dataset_id,
        evaluation_request=default_request(),
        history=[],
    )


def test_direct_answer_preserves_model_and_usage():
    snapshot = golden_snapshot()
    client = FakeClient([{
        "choices": [{"message": {"role": "assistant", "content": "Start with the CPU migration pilot."}}],
        "model": "deepseek-fixture",
        "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
    }])

    result = run_chat(snapshot, not_run_investigation(snapshot.dataset_id), payload(), client)

    assert result.answer == "Start with the CPU migration pilot."
    assert result.model == "deepseek-fixture"
    assert result.usage.total_tokens == 20
    assert result.tool_calls == []


def test_tool_call_receives_real_decision_summary_before_final_answer():
    snapshot = golden_snapshot()
    client = FakeClient([
        {
            "choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call-1", "type": "function",
                "function": {"name": "get_decision_summary", "arguments": "{}"},
            }]}}],
            "model": "deepseek-fixture",
            "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13},
        },
        {
            "choices": [{"message": {"role": "assistant", "content": "The default CPU scenario recovers 15 GPU-hours at the point estimate."}}],
            "model": "deepseek-fixture",
            "usage": {"prompt_tokens": 30, "completion_tokens": 11, "total_tokens": 41},
        },
    ])

    result = run_chat(snapshot, not_run_investigation(snapshot.dataset_id), payload(), client)

    tool_message = client.calls[1]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert '"point":15' in tool_message["content"]
    assert result.tool_calls[0].tool_name == "get_decision_summary"
    assert result.tool_calls[0].status == "success"
    assert result.usage.total_tokens == 54


def test_unknown_tool_is_returned_as_a_controlled_tool_error():
    snapshot = golden_snapshot()
    client = FakeClient([
        {
            "choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call-x", "type": "function",
                "function": {"name": "delete_cluster", "arguments": "{}"},
            }]}}],
            "model": "deepseek-fixture", "usage": {},
        },
        {
            "choices": [{"message": {"role": "assistant", "content": "That operation is not available."}}],
            "model": "deepseek-fixture", "usage": {},
        },
    ])

    result = run_chat(snapshot, not_run_investigation(snapshot.dataset_id), payload(), client)

    assert result.tool_calls[0].status == "error"
    assert result.tool_calls[0].error == "Unknown or unavailable tool."


def test_list_findings_validates_and_forwards_a_bounded_limit(monkeypatch):
    class Result:
        def model_dump(self, mode="json"):
            return {"success": True, "total": 0, "findings": []}

    observed = {}
    def fake_findings(request):
        observed["limit"] = request.limit
        observed["detector_id"] = request.detector_id
        return Result()

    monkeypatch.setattr("api.main.findings", fake_findings)
    snapshot = golden_snapshot()
    client = FakeClient([
        {
            "choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call-findings", "type": "function",
                "function": {"name": "list_findings", "arguments": '{"detector_id":"rules::gpu-not-needed","limit":2}'},
            }]}}],
            "model": "deepseek-fixture", "usage": {},
        },
        {
            "choices": [{"message": {"role": "assistant", "content": "No matching findings."}}],
            "model": "deepseek-fixture", "usage": {},
        },
    ])

    result = run_chat(snapshot, not_run_investigation(snapshot.dataset_id), payload(), client)

    assert result.tool_calls[0].status == "success"
    assert observed == {"limit": 2, "detector_id": "rules::gpu-not-needed"}


def test_tool_round_limit_stops_a_runaway_agent():
    snapshot = golden_snapshot()
    tool_response = {
        "choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [{
            "id": "call-loop", "type": "function",
            "function": {"name": "get_decision_summary", "arguments": "{}"},
        }]}}],
        "model": "deepseek-fixture", "usage": {},
    }
    client = FakeClient([tool_response, tool_response, tool_response])

    with pytest.raises(DecisionError) as raised:
        run_chat(snapshot, not_run_investigation(snapshot.dataset_id), payload(), client)

    assert raised.value.code == "AGENT_LIMIT_REACHED"


def test_client_requires_key_without_exposing_secret(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(DecisionError) as raised:
        DeepSeekClient.from_env()
    assert raised.value.code == "AGENT_NOT_CONFIGURED"
    assert "key" not in raised.value.details
