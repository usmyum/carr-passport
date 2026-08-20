"""The single place where exceptions become HTTP responses.

Registered once in `main.py`. Keeping it here means routers stay free of
try/except blocks and every error in the API shares one response shape.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.shared.exceptions import AppException

logger = logging.getLogger(__name__)


def error_response(
        status_code: int,
        error_code: str,
        detail: str,
        errors: list | None = None,
) -> JSONResponse:
    payload: dict = {
        "error": {
            "code": error_code,
            "message": detail,
        }
    }

    if errors:
        payload["error"]["details"] = errors

    return JSONResponse(
        status_code=status_code,
        content=payload,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(
            request: Request,
            exc: AppException,
    ) -> JSONResponse:
        return error_response(
            status_code=exc.status_code,
            error_code=exc.error_code,
            detail=exc.detail,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
            request: Request,
            exc: RequestValidationError,
    ) -> JSONResponse:
        return error_response(
            status_code=422,
            error_code="validation_error",
            detail="The submitted data is not valid",
            errors=[
                {
                    "field": ".".join(
                        str(part) for part in error["loc"][1:]
                    ),
                    "message": error["msg"],
                }
                for error in exc.errors()
            ],
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
            request: Request,
            exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "Unhandled error on %s %s",
            request.method,
            request.url.path,
        )

        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="internal_error",
            detail="Something went wrong",
        )
