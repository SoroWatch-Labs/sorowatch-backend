"""
Structured JSON request logging.

Emits one JSON line per request on the "sorowatch.access" logger with the
method, path, status code, duration and a request ID. The request ID is
taken from an incoming X-Request-ID header (so it can be traced across
services) or generated, and is echoed back in the response headers.

Headers, query strings and bodies are deliberately NOT logged, so secrets
such as the X-API-Key never end up in the logs.
"""
import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("sorowatch.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        start = time.perf_counter()
        status_code = 500  # reported if the handler raises
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                json.dumps(
                    {
                        "event": "request",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": status_code,
                        "duration_ms": duration_ms,
                        "client": request.client.host if request.client else None,
                    }
                )
            )
