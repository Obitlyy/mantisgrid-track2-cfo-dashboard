# Controlled DeepSeek Chat Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal read-only DeepSeek tool-calling chat assistant to the completed Track 2 application.

**Architecture:** Keep the deterministic decision stack authoritative. Add a small DeepSeek HTTP client, a bounded agent loop over curated existing tools, one typed route, and one frontend panel.

**Tech Stack:** FastAPI, Pydantic, httpx, React, TypeScript, Vitest, pytest, DeepSeek Chat Completions.

**Spec:** `docs/superpowers/specs/2026-09-17-controlled-chat-agent-design.md`

## Global Constraints

- Never persist, print, return, or commit `DEEPSEEK_API_KEY`.
- No streaming, database, authentication subsystem, arbitrary tool execution, scheduler action, or new financial calculation.
- Existing dashboard and APIs must remain usable without an LLM key.

### Task 1: Backend contracts and bounded agent loop

**Files:** Create `track-2/decision/deepseek_client.py`, `track-2/decision/chat_agent.py`; modify `contracts.py`; test `track-2/tests/test_chat_agent.py`.

**Interfaces:** `run_chat(snapshot, investigation, payload, client) -> ChatResponse`; `DeepSeekClient.complete(messages, tools) -> dict`.

- [ ] Write failing tests for one tool round, direct response, malformed/unknown tool, limits, and missing configuration.
- [ ] Run the focused test and confirm the expected missing-feature failure.
- [ ] Implement the minimal contracts, HTTP adapter, system prompt, curated tools, and bounded loop.
- [ ] Run the focused tests and the existing decision test suite.

### Task 2: Typed HTTP route and configuration

**Files:** Modify `routes.py`, `docker-compose.yml`, `.env.example`, `README.md`; test `track-2/tests/test_routes.py`.

**Interfaces:** `POST /v1/decision/chat`, `ChatRequest -> ChatResponse`.

- [ ] Write a failing route test with dependency-injected fake model client.
- [ ] Add the route and environment-only configuration.
- [ ] Verify missing key is isolated to chat and evaluate remains healthy.

### Task 3: Minimal dashboard panel

**Files:** Create `dashboard/src/components/ChatAgentPanel.tsx`; modify `api/client.ts`, `App.tsx`, `styles.css`; test `dashboard/src/__tests__/chat-agent.test.tsx`.

**Interfaces:** `askAgent(message, evaluation, history, signal) -> ChatResponse`.

- [ ] Write a failing component test for answer, receipt, usage, and non-destructive error display.
- [ ] Add the client and accessible panel using the applied evaluation only.
- [ ] Run typecheck, Vitest, and production build.

### Task 4: Contract generation and final verification

**Files:** Regenerate `decision.schema.json`, `openapi.json`, `contracts.generated.ts`.

- [ ] Run contract generation without data/MCP/network side effects.
- [ ] Run focused backend/frontend tests, then the existing suites.
- [ ] Check git diff for secrets and unrelated changes; do not modify the user's existing `dashboard/nginx.conf` change.
