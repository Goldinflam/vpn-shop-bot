"""Tenacity retry helpers for the XUI client.

Single re-login retry on authentication failure. We intentionally keep this
narrow: network/5xx retries are handled inside ``py3xui`` itself, and the
only extra behaviour we care about is a transparent session refresh on 401.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from shared.contracts.errors import XUIAuthError

T = TypeVar("T")


async def retry_on_auth(
    action: Callable[[], Awaitable[T]],
    relogin: Callable[[], Awaitable[None]],
) -> T:
    """Run *action*; on :class:`XUIAuthError` re-login once and retry.

    This is a hand-rolled one-shot retry because ``tenacity`` does not play
    nicely with async closures that also need access to the parent ``self``.
    The semantics are identical to a ``tenacity.AsyncRetrying`` with
    ``stop_after_attempt(2)`` and a ``retry_if_exception_type(XUIAuthError)``.
    """
    try:
        return await action()
    except XUIAuthError:
        await relogin()
        return await action()
