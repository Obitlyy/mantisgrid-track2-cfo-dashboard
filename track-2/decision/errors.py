from __future__ import annotations


class DecisionError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None, http_status: int = 500):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.http_status = http_status
