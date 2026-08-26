import contextvars
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


request_id_ctx_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


def get_request_id() -> str:
    return request_id_ctx_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    HEADER_NAME = "X-Trace-ID"  # renamed from X-Request-ID: this is now literally the OTel trace ID

    async def dispatch(self, request: Request, call_next):
        span_context = trace.get_current_span().get_span_context()

        if span_context.trace_id != 0:
            # OTel trace IDs are 128-bit ints; format as the standard 32-char hex string
            # (this is the same format you'll see in the Jaeger UI's search box)
            request_id = format(span_context.trace_id, "032x")
        else:
            # No active span — e.g. tracing not set up yet, or this route was
            # excluded from instrumentation. Falls back to "-" rather than
            # inventing a disconnected ID that would just recreate the old problem.
            request_id = "-"

        token = request_id_ctx_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx_var.reset(token)

        response.headers[self.HEADER_NAME] = request_id
        return response
