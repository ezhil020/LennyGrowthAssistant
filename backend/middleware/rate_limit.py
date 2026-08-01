"""
middleware/rate_limit.py — In-memory sliding window rate limiter.

Limits requests per IP address. No Redis required — uses a simple
in-memory dict with cleanup. For production scale, switch to Redis.
"""

import time
from collections import defaultdict, deque

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.config import settings

logger = structlog.get_logger(__name__)

# IP → deque of timestamps (seconds) for the sliding window
_request_log: dict[str, deque] = defaultdict(deque)
_WINDOW_SECONDS = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = None):
        super().__init__(app)
        self._limit = requests_per_minute or settings.rate_limit_per_minute

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks
        if request.url.path == "/api/v1/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = _request_log[client_ip]

        # Remove timestamps outside the window
        while window and now - window[0] > _WINDOW_SECONDS:
            window.popleft()

        if len(window) >= self._limit:
            logger.warning("rate_limit_exceeded", ip=client_ip, count=len(window))
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Please wait before sending another request."},
                headers={"Retry-After": str(_WINDOW_SECONDS)},
            )

        window.append(now)
        return await call_next(request)
