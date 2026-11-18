"""A small fixed-window rate limiter, used as a FastAPI dependency.

    @router.post("/login", dependencies=[Depends(rate_limit("login", 10, 60))])

In-memory, so the counts live in one process. That's right for one API
instance; running several (or several uvicorn workers) needs a shared store
like Redis behind the same `rate_limit()` interface.
"""

import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import Request

from app.shared.exceptions import TooManyRequestsException

# (scope, client) -> (window start, hits in that window)
_hits: dict[tuple[str, str], tuple[float, int]] = defaultdict(lambda: (0.0, 0))


def rate_limit(
    scope: str,
    max_requests: int,
    window_seconds: int,
) -> Callable[[Request], None]:
    """Allow `max_requests` per client IP per `window_seconds` for `scope`."""

    def dependency(request: Request) -> None:

        # Behind a proxy/load balancer this is the proxy's IP; run uvicorn
        # with --proxy-headers there so it reflects the real client.
        client = request.client.host if request.client else "unknown"

        key = (scope, client)
        now = time.monotonic()

        window_start, count = _hits[key]

        if now - window_start >= window_seconds:
            window_start, count = now, 0

        if count >= max_requests:
            retry_after = int(window_seconds - (now - window_start)) + 1
            raise TooManyRequestsException(
                f"Too many attempts. Try again in {retry_after} seconds."
            )

        _hits[key] = (window_start, count + 1)

    return dependency


def reset_rate_limits() -> None:
    """Forget every count. For tests."""

    _hits.clear()
