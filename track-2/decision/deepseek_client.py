from __future__ import annotations

import os

import httpx

from decision.errors import DecisionError


class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout_sec: float = 25):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self.model = model
        self._timeout_sec = timeout_sec

    @classmethod
    def from_env(cls) -> "DeepSeekClient":
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise DecisionError(
                "AGENT_NOT_CONFIGURED",
                "The chat agent is not configured.",
                {},
                503,
            )
        return cls(
            api_key=api_key,
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            model=os.environ.get("DEEPSEEK_MODEL", "deepseek-flash"),
        )

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "thinking": {"type": "disabled"},
            "temperature": 0.1,
            "max_tokens": 900,
            "stream": False,
        }
        try:
            with httpx.Client(timeout=self._timeout_sec) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            raise DecisionError(
                "LLM_UPSTREAM_ERROR",
                "The chat model request failed.",
                {"upstream_status": status} if status else {},
                502,
            ) from exc
        if not isinstance(body, dict):
            raise DecisionError("LLM_UPSTREAM_ERROR", "The chat model returned an invalid response.", {}, 502)
        return body
