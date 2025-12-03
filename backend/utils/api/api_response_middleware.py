# utils/api/api_response_middleware.py

import json
import time
import uuid
import logging
from typing import Any, Iterable, AsyncIterable
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import ValidationError
from models.api_models import ApiResponse, ErrorResponse, ErrorDetail, PaginatedData
from utils.appwide.errors import AppException
from utils.appwide.request_context import set_request_id, get_request_id


# ---------------------------------------------------------
# Logging Filter
# ---------------------------------------------------------
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id()
        return True


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(request_id)s] %(name)s: %(message)s'
)
for handler in logging.getLogger().handlers:
    handler.addFilter(RequestIdFilter())

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------
SENSITIVE_FIELDS = {"password", "token", "access_token", "refresh_token", "secret", "api_key"}
MAX_LOG_LENGTH = 2000


def mask_sensitive(data: Any):
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    if isinstance(data, dict):
        return {
            k: ("***MASKED***" if k in SENSITIVE_FIELDS else mask_sensitive(v))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [mask_sensitive(item) for item in data]
    return data


def trim(text: str):
    return text if len(text) <= MAX_LOG_LENGTH else text[:MAX_LOG_LENGTH] + "...(truncated)"


def paginate(data, page: int, page_size: int):
    if not isinstance(data, list):
        return data

    total = len(data)
    start, end = (page - 1) * page_size, page * page_size

    return PaginatedData(
        items=data[start:end],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        has_next=end < total,
        has_prev=start > 0,
    )


ERROR_CODE_MAP = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    500: "internal_server_error",
}


# helper to create an async iterator over single bytes object
def _make_async_body_iterator(resp_body: bytes) -> AsyncIterable[bytes]:
    async def _iter():
        yield resp_body
    return _iter()


# ---------------------------------------------------------
# Global Middleware
# ---------------------------------------------------------
class GlobalResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        set_request_id(request_id)
        start = time.perf_counter()

        # pagination params (defaults)
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))

        # Read request body for logging and allow downstream to read it again
        try:
            body_raw = await request.body()
            body_text = trim(body_raw.decode("utf-8", errors="replace"))
        except Exception:
            body_raw = b""
            body_text = "<unreadable>"

        logger.info(f"Incoming {request.method} {request.url} Body={body_text}")

        # Rebuild request so endpoint can read the body again
        request = Request(request.scope, receive=lambda: {"type": "http.request", "body": body_raw})

        try:
            raw_response: Response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            # If endpoint explicitly opted-out, return raw response untouched.
            if raw_response.headers.get("X-No-Wrap") == "true":
                return raw_response

            # Read the response body (consume the iterator)
            resp_body = b""
            async for chunk in raw_response.body_iterator:
                # chunk may be bytes or memoryview
                if isinstance(chunk, memoryview):
                    resp_body += chunk.tobytes()
                else:
                    resp_body += chunk

            resp_text = resp_body.decode("utf-8", errors="replace")
            logger.info(f"Response {raw_response.status_code} Duration={duration_ms}ms Body={trim(resp_text)}")

            # Try to parse JSON regardless of media_type (fixes data==null issue)
            try:
                data = json.loads(resp_text)
            except Exception:
                # Not JSON — restore async body iterator and return raw response
                raw_response.body_iterator = _make_async_body_iterator(resp_body)
                return raw_response

            # If already in ApiResponse shape, don't re-wrap
            if isinstance(data, dict) and "success" in data and "timestamp" in data:
                raw_response.body_iterator = _make_async_body_iterator(resp_body)
                return raw_response

            # Apply masking 
            masked = mask_sensitive(data)

            # Apply pagination only if "page" or "page_size" are explicitly provided
            # Calls with ?page=1&page_size=20 return the paginated structure with items.
            if "page" in request.query_params or "page_size" in request.query_params:
                masked = paginate(masked, page, page_size)
            

            wrapped = ApiResponse(success=True, message="OK", data=masked).model_dump()

            # Return JSONResponse preserving original headers (except hop-by-hop)
            headers = dict(raw_response.headers)
            # Optionally remove/adjust headers that aren't valid on new response
            for h in ("content-length", "transfer-encoding", "content-encoding"):
                headers.pop(h, None)

            return JSONResponse(status_code=raw_response.status_code, content=wrapped, headers=headers)

        except ValidationError as e:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            err = ErrorResponse(
                message="Validation Error",
                error=ErrorDetail(code="validation_error", message=str(e), details=e.errors())
            ).model_dump()
            err["request_id"] = request_id
            err["duration_ms"] = duration_ms
            logger.error(f"[{request_id}] ValidationError: {str(e)}")
            return JSONResponse(status_code=422, content=err)

        except AppException as e:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(f"[{request_id}] AppException: {e.message}")
            err = {
                "success": False,
                "message": "Internal Server Error",
                "error": {"code": e.code, "message": e.message, "details": e.details},
                "request_id": request_id,
                "duration_ms": duration_ms,
            }
            return JSONResponse(status_code=500, content=err)

        except Exception as ex:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(f"[{request_id}] Unhandled Exception: {ex}")
            err = {
                "success": False,
                "message": "Internal Server Error",
                "error": {
                    "code": ERROR_CODE_MAP.get(500, "error"),
                    "message": "An internal error occurred",
                    "details": repr(ex),
                },
                "request_id": request_id,
                "duration_ms": duration_ms,
            }
            return JSONResponse(status_code=500, content=err)
