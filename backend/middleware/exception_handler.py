"""
middleware/exception_handler.py — Global exception handler.

Catches all unhandled exceptions and returns a user-facing JSON error.
Never exposes stack traces or internal exception text to clients.
"""

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "An unexpected error occurred. Please try again.",
            "request_id": request_id,
        },
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning("value_error", request_id=request_id, error=str(exc))
    return JSONResponse(
        status_code=404,
        content={"error": str(exc), "request_id": request_id},
    )


async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("runtime_error", request_id=request_id, error=str(exc))
    return JSONResponse(
        status_code=503,
        content={"error": str(exc), "request_id": request_id},
    )
