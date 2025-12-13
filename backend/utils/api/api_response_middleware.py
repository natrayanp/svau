# utils/api/api_response_middleware.py

import json
import time
import uuid
import logging
from typing import Any, AsyncIterable, Dict
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import ValidationError
from models.api_models import ApiResponse, PaginatedData
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

def mask_sensitive(data: Any) -> Any:
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    if isinstance(data, dict):
        return {k: ("***MASKED***" if k in SENSITIVE_FIELDS else mask_sensitive(v)) for k, v in data.items()}
    if isinstance(data, list):
        return [mask_sensitive(v) for v in data]
    return data

def trim(text: str) -> str:
    return text if len(text) <= MAX_LOG_LENGTH else text[:MAX_LOG_LENGTH] + "...(truncated)"

def _make_async_body_iterator(resp_body: bytes) -> AsyncIterable[bytes]:
    async def _iter():
        yield resp_body
    return _iter()

def make_json_response(status_code: int, content: dict, request_id: str, headers: dict = None) -> JSONResponse:
    response = JSONResponse(status_code=status_code, content=content, headers=headers)
    response.headers["X-Request-ID"] = request_id
    return response

# ---------------------------------------------------------
# Global Middleware
# ---------------------------------------------------------
class GlobalResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)
        start_time = time.perf_counter()

        # Read request body for logging
        try:
            body_raw = await request.body()
            body_text = trim(body_raw.decode("utf-8", errors="replace"))
        except Exception:
            body_raw = b""
            body_text = "<unreadable>"

        logger.info(f"Incoming {request.method} {request.url} Body={body_text}")

        # Rebuild request for downstream
        request = Request(request.scope, receive=lambda: {"type": "http.request", "body": body_raw})

        try:
            response: Response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Opt-out of wrapping
            if response.headers.get("X-No-Wrap") == "true":
                return response

            # Read response body
            resp_body = b""
            async for chunk in response.body_iterator:
                resp_body += chunk.tobytes() if isinstance(chunk, memoryview) else chunk

            resp_text = resp_body.decode("utf-8", errors="replace")
            logger.info(f"Response {response.status_code} Duration={duration_ms}ms Body={trim(resp_text)}")

            # Parse JSON
            try:
                data = json.loads(resp_text)
            except Exception:
                response.body_iterator = _make_async_body_iterator(resp_body)
                return response
            print("data", data)
            # Already wrapped
            if isinstance(data, dict) and "success" in data and "timestamp" in data:
                print("success inside")
                response.body_iterator = _make_async_body_iterator(resp_body)
                return response

            # Extract operation_metadata if present
            op_meta = None
            if isinstance(data, dict) and "operation_metadata" in data:
                print("op_meta inside")
                op_meta = data.pop("operation_metadata")

            print("op_meta", op_meta)

            # Data extraction:
            # - Single-key dict → value
            # - PaginatedData → keep as-is
            extracted_data = data
            if isinstance(data, dict):
                paginated_keys = {"items", "total", "page", "page_size", "total_pages", "has_next", "has_prev"}
                if paginated_keys.issubset(data.keys()):
                    extracted_data = data  # keep PaginatedData
                elif len(data) == 1:
                    extracted_data = next(iter(data.values()))

            # Mask sensitive fields
            masked_data = mask_sensitive(extracted_data)

            wrapped = ApiResponse(
                success=True,
                message="OK",
                data=masked_data,
                operation_metadata=op_meta
            ).model_dump()

            # Preserve headers except hop-by-hop
            headers = dict(response.headers)
            for h in ("content-length", "transfer-encoding", "content-encoding"):
                headers.pop(h, None)

            return make_json_response(response.status_code, wrapped, request_id, headers)

        # -------------------------------
        # Error Handling
        # -------------------------------
        except ValidationError as e:
            logger.error(f"[{request_id}] ValidationError: {e}")
            return make_json_response(422, {
                "success": False,
                "message": "Validation Error",
                "error": {"code": "validation_error", "message": str(e), "details": e.errors()},
                "request_id": request_id,
                "duration_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }, request_id)

        except AppException as e:
            logger.error(f"[{request_id}] AppException: {e.message}")
            return make_json_response(500, {
                "success": False,
                "message": "Internal Server Error",
                "error": {"code": e.code, "message": e.message, "details": e.details},
                "request_id": request_id,
                "duration_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }, request_id)

        except Exception as e:
            logger.exception(f"[{request_id}] Unhandled Exception: {e}")
            return make_json_response(500, {
                "success": False,
                "message": "Internal Server Error",
                "error": {"code": "internal_server_error", "message": "An internal error occurred", "details": repr(e)},
                "request_id": request_id,
                "duration_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }, request_id)
