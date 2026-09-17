# Controlled DeepSeek Chat Agent Design

## Goal

Add a small read-only conversational assistant to the completed Track 2 dashboard. The assistant answers basic questions about the currently applied scenario by calling the existing deterministic Decision API and official MantisGrid evidence interfaces; it never invents financial calculations or operates the cluster.

## Architecture

The existing dashboard, analysis, claims, and MCP audit remain authoritative. A new `POST /v1/decision/chat` endpoint invokes DeepSeek's OpenAI-compatible Chat Completions API with a fixed system prompt and a curated function set. The server executes at most three tool rounds, validates every argument, and returns the answer together with model, token usage, and tool receipts. The browser keeps only short display history and sends the current applied `EvaluationRequest`; no database or server-side conversation state is added.

## Configuration

- `DEEPSEEK_API_KEY`: required only for chat; never committed or returned.
- `DEEPSEEK_BASE_URL=https://api.deepseek.com`
- `DEEPSEEK_MODEL=deepseek-flash`
- If the key is absent, the dashboard and Decision API still work; chat reports `AGENT_NOT_CONFIGURED`.

## Curated tools

- `get_decision_summary`: deterministic baseline, selected actions, portfolio recovery, reference savings, risk unknowns, and sample caveats.
- `list_findings`: official Layer A finding query with bounded filters and at most ten rows.
- `get_causal`: official Layer A causal lookup for one finding.
- `get_job_detail`: existing decision evidence for one job in the loaded dataset.
- `get_finding_detail`: existing decision evidence for one finding in the loaded dataset.
- `get_mcp_investigation`: current cached bounded MCP investigation.

## Safety and limits

- Read-only; no drain, cancel, migration, scheduler, filesystem, shell, or arbitrary HTTP tool.
- Maximum 2,000 characters per user message, six prior turns, three model rounds, six total tool calls, ten findings per query, and 900 output tokens.
- Tool arguments use strict local validation even if the model emits malformed JSON.
- Numeric claims must come from tool results. The prompt labels all money as reference-priced, all recovery intervals as scenarios, and all data as a historical sample.
- A model failure does not affect existing dashboard readiness.

## Minimal UI

An `Ask the cluster` panel below the decision views contains starter questions, a text input, send button, answer history, tool names, and token usage. Responses are rendered as plain text. The applied scenario is captured when Send is pressed, so drafts cannot contaminate the answer.

## Acceptance

- A mocked model tool call receives a real deterministic tool result and produces a final answer.
- Missing key, invalid tool arguments, unknown tools, upstream failure, and tool-round exhaustion return controlled errors.
- The UI can ask a question, show an answer and receipts, and preserve the main dashboard on chat failure.
- Existing Python and frontend tests remain green; no live key is required for automated tests.
