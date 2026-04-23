"""Exceptions raised by :class:`bot.api_client.BackendClient`."""

from __future__ import annotations


class BackendError(Exception):
    """Generic backend-side error (non-2xx response)."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"backend returned {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class BackendUnavailableError(BackendError):
    """Backend is unreachable or timed out."""

    def __init__(self, message: str) -> None:
        super().__init__(status_code=0, message=message)


class NotFoundError(BackendError):
    """Backend returned 404 for the requested resource."""


class ValidationError(BackendError):
    """Backend returned 422 (request body failed validation)."""


class AuthError(BackendError):
    """Backend returned 401/403 — token mismatch or admin token required."""
