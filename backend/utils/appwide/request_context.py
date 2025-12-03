# utils/common/request_context.py

from contextvars import ContextVar

# Context variable for request ID
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="NO-RID")


def set_request_id(rid: str):
    """Set the current request ID in context."""
    request_id_ctx.set(rid)


def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_ctx.get()
