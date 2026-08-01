"""middleware/timing_middleware.py — Adds X-Process-Time header to all responses."""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        response.headers["X-Process-Time"] = f"{duration_ms}ms"
        return response
