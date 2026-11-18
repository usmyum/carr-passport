"""Logging setup and the request-ID middleware.

Every log line carries the request ID of the request that produced it, and
every response returns it as `X-Request-ID` — so a user's error report can
be matched to the exact log lines behind it.

Locally logs are human-readable; anywhere else they're one JSON object per
line, which log tools (CloudWatch, Datadog, Loki…) can search by field.
"""

import json
import logging
import time
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request, Response

from app.core.config import settings

REQUEST_ID_HEADER = "X-Request-ID"

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

logger = logging.getLogger("app.request")


class RequestIdFilter(logging.Filter):
    """Stamps the current request's ID onto every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):

    # Attributes every LogRecord has — anything else was passed via `extra=`.
    _STANDARD = set(vars(logging.makeLogRecord({}))) | {"message", "request_id"}

    def format(self, record: logging.LogRecord) -> str:

        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }

        payload.update(
            (key, value)
            for key, value in vars(record).items()
            if key not in self._STANDARD
        )

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging() -> None:

    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())

    if settings.is_local:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-5s [%(request_id)s] %(name)s: %(message)s"
            )
        )
    else:
        handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)

    # Uvicorn's own access log would duplicate the request line below,
    # without the request ID.
    logging.getLogger("uvicorn.access").disabled = True

    # Every SQL statement, locally only — handy while learning, far too
    # noisy (and potentially sensitive) anywhere else.
    if settings.is_local:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


def register_request_logging(app: FastAPI) -> None:

    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:

        # Reuse an ID from an upstream proxy/client if there is one, so one
        # request can be traced across services. Each request runs in its
        # own task, so setting the contextvar here can't leak into another
        # request — and it stays set for the 500 handler's log line too.
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request_id_var.set(request_id)

        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            # The global handler turns this into the 500 response and logs
            # the traceback; this keeps the one-line-per-request log complete.
            _log_request(request, 500, started)
            raise

        response.headers[REQUEST_ID_HEADER] = request_id

        _log_request(request, response.status_code, started)

        return response


def _log_request(request: Request, status: int, started: float) -> None:

    duration_ms = round((time.perf_counter() - started) * 1000, 1)

    logger.info(
        "%s %s -> %s (%sms)",
        request.method,
        request.url.path,
        status,
        duration_ms,
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": status,
            "duration_ms": duration_ms,
        },
    )
