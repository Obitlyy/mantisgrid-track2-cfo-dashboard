from __future__ import annotations

import json
from typing import Any

from decision.contracts import (
    ChatRequest,
    ChatResponse,
    ChatToolReceipt,
    ChatUsage,
    Investigation,
)
from decision.errors import DecisionError
from decision.service import evaluate, finding_detail, job_detail

MAX_ROUNDS = 3
MAX_TOOL_CALLS = 6

SYSTEM_PROMPT = """You are a read-only GPU efficiency analyst for the Track 2 historical sample.
Use the provided tools before stating dataset-specific numbers. Treat get_decision_summary as the
authoritative source for money and recovery scenarios. Treat official Layer A findings and causal
results as evidence; a missing causal chain means cannot determine, not healthy. Never add finding
impact values, never describe scenario reference savings as realized cash, and never claim the
sample represents the whole cluster. Do not propose executing drain, cancel, migration, or scheduler
changes. Give concise English answers and cite finding IDs or job IDs when a tool returned them."""


TOOLS = [
    {"type": "function", "function": {"name": "get_decision_summary", "description": "Get the authoritative deterministic baseline, selected actions, recovery scenario, reference savings, risks and caveats for the applied scenario.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "list_findings", "description": "Query official Layer A findings. Returns at most ten evidence records; do not sum their impact values.", "parameters": {"type": "object", "properties": {"detector_id": {"type": "string"}, "category": {"type": "string"}, "severity": {"type": "string"}, "resource_id": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 10}}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "get_causal", "description": "Run official authoritative Layer A causal analysis for one finding ID.", "parameters": {"type": "object", "properties": {"finding_id": {"type": "string"}}, "required": ["finding_id"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "get_job_detail", "description": "Get one job and its physical GPU evidence by decimal job ID.", "parameters": {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "get_finding_detail", "description": "Get one normalized finding and its linked jobs, nodes and root causes.", "parameters": {"type": "object", "properties": {"finding_id": {"type": "string"}}, "required": ["finding_id"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "get_mcp_investigation", "description": "Get the current bounded MCP node recommendation audit and its limitations.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
]


def _decision_summary(evaluation) -> dict:
    return {
        "dataset_id": evaluation.meta.dataset_id,
        "evaluation_id": evaluation.meta.evaluation_id,
        "sample_window": evaluation.meta.sample_window.model_dump(mode="json"),
        "baseline": {
            "measured_gpu_hours": evaluation.baseline.measured_gpu_hours,
            "reference_cost_usd": evaluation.baseline.reference_cost_usd,
            "outcomes": [x.model_dump(mode="json") for x in evaluation.baseline.outcomes],
            "caveats": evaluation.baseline.caveats,
        },
        "actions": [{
            "action_id": action.action_id,
            "title": action.title,
            "owner_role": action.owner_role,
            "candidate_jobs": action.candidate_jobs,
            "candidate_gpu_hours": action.candidate_gpu_hours,
            "standalone_recoverable_gpu_hours": action.standalone_recoverable_gpu_hours.model_dump(mode="json"),
            "marginal_recoverable_gpu_hours": action.marginal_recoverable_gpu_hours.model_dump(mode="json") if action.marginal_recoverable_gpu_hours else None,
            "warnings": action.warnings,
        } for action in evaluation.actions],
        "portfolio": evaluation.portfolio.model_dump(mode="json"),
        "audit_status": evaluation.audit_status,
        "warnings": evaluation.warnings,
    }


def _execute_tool(name: str, arguments: dict, snapshot, evaluation, investigation: Investigation) -> Any:
    if name == "get_decision_summary":
        if arguments: raise ValueError("This tool takes no arguments.")
        return _decision_summary(evaluation)
    if name == "get_mcp_investigation":
        if arguments: raise ValueError("This tool takes no arguments.")
        return investigation.model_dump(mode="json")
    if name == "get_job_detail":
        if set(arguments) != {"job_id"}: raise ValueError("job_id is required.")
        return job_detail(snapshot, str(arguments["job_id"])).model_dump(mode="json")
    if name == "get_finding_detail":
        if set(arguments) != {"finding_id"}: raise ValueError("finding_id is required.")
        return finding_detail(snapshot, str(arguments["finding_id"])).model_dump(mode="json")
    if name == "list_findings":
        allowed = {"detector_id", "category", "severity", "resource_id", "limit"}
        if not set(arguments) <= allowed: raise ValueError("Unsupported finding filter.")
        limit = int(arguments.get("limit", 5))
        if not 1 <= limit <= 10: raise ValueError("limit must be between 1 and 10.")
        from api.main import findings
        from api.models import FindingsRequest
        filters = {key: value for key, value in arguments.items() if key != "limit"}
        result = findings(FindingsRequest(**filters, limit=limit, offset=0))
        return result.model_dump(mode="json")
    if name == "get_causal":
        if set(arguments) != {"finding_id"}: raise ValueError("finding_id is required.")
        from api.main import causal
        from api.models import CausalRequest
        return causal(CausalRequest(finding_id=str(arguments["finding_id"]), hop_count=3)).model_dump(mode="json")
    raise ValueError("Unknown or unavailable tool.")


def _usage(payload: dict) -> ChatUsage:
    value = payload.get("usage") or {}
    prompt = int(value.get("prompt_tokens", 0) or 0)
    completion = int(value.get("completion_tokens", 0) or 0)
    return ChatUsage(prompt_tokens=prompt, completion_tokens=completion,
                     total_tokens=int(value.get("total_tokens", prompt + completion) or 0))


def run_chat(snapshot, investigation: Investigation, payload: ChatRequest, client) -> ChatResponse:
    if payload.dataset_id != snapshot.dataset_id:
        raise DecisionError("DATASET_MISMATCH", "Chat dataset does not match the loaded dataset.", {}, 409)
    evaluation = evaluate(snapshot, payload.evaluation_request, investigation)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(turn.model_dump(mode="json") for turn in payload.history)
    messages.append({"role": "user", "content": payload.message})
    receipts: list[ChatToolReceipt] = []
    total_usage = ChatUsage()

    for _ in range(MAX_ROUNDS):
        response = client.complete(messages, TOOLS)
        usage = _usage(response)
        total_usage = ChatUsage(
            prompt_tokens=total_usage.prompt_tokens + usage.prompt_tokens,
            completion_tokens=total_usage.completion_tokens + usage.completion_tokens,
            total_tokens=total_usage.total_tokens + usage.total_tokens,
        )
        choices = response.get("choices") or []
        if not choices or not isinstance(choices[0].get("message"), dict):
            raise DecisionError("LLM_UPSTREAM_ERROR", "The chat model returned no message.", {}, 502)
        assistant = choices[0]["message"]
        calls = assistant.get("tool_calls") or []
        if not calls:
            answer = str(assistant.get("content") or "").strip()
            if not answer:
                raise DecisionError("LLM_UPSTREAM_ERROR", "The chat model returned an empty answer.", {}, 502)
            return ChatResponse(meta=evaluation.meta, answer=answer,
                                model=str(response.get("model") or client.model),
                                usage=total_usage, tool_calls=receipts)
        messages.append({"role": "assistant", "content": assistant.get("content"), "tool_calls": calls})
        for call in calls:
            if len(receipts) >= MAX_TOOL_CALLS:
                raise DecisionError("AGENT_LIMIT_REACHED", "The chat agent reached its tool-call limit.", {}, 422)
            function = call.get("function") or {}
            name = str(function.get("name") or "")
            arguments: dict = {}
            try:
                arguments = json.loads(function.get("arguments") or "{}")
                if not isinstance(arguments, dict): raise ValueError("Tool arguments must be an object.")
                result = _execute_tool(name, arguments, snapshot, evaluation, investigation)
                receipt = ChatToolReceipt(tool_name=name, arguments=arguments, status="success")
                content = json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            except Exception as exc:
                message = "Unknown or unavailable tool." if name not in {t["function"]["name"] for t in TOOLS} else str(exc)
                receipt = ChatToolReceipt(tool_name=name or "unknown", arguments=arguments, status="error", error=message)
                content = json.dumps({"error": message}, separators=(",", ":"))
            receipts.append(receipt)
            messages.append({"role": "tool", "tool_call_id": str(call.get("id") or "unknown"), "content": content[:16000]})

    raise DecisionError("AGENT_LIMIT_REACHED", "The chat agent reached its reasoning-round limit.", {}, 422)
