"""Domain exceptions.

Services raise these. Routers never catch them — the global handler registered
in `main.py` turns each one into the right HTTP response.
"""

from fastapi import status


class AppException(Exception):
    """Base class for every domain error the API knows how to answer with."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail: str = "Something went wrong"
    error_code: str = "internal_error"

    def __init__(
        self,
        detail: str | None = None,
    ):
        self.detail = detail or self.default_detail

        super().__init__(self.detail)


class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found"
    error_code = "not_found"


class ConflictException(AppException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource already exists"
    error_code = "conflict"


class ValidationException(AppException):
    # Literal, not status.HTTP_422_*: Starlette renamed the constant.
    status_code = 422
    default_detail = "The submitted data is not valid"
    error_code = "validation_error"


class UnauthorizedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication required"
    error_code = "unauthorized"


class ForbiddenException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have access to this resource"
    error_code = "forbidden"


class TooManyRequestsException(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Too many requests. Try again later."
    error_code = "rate_limited"


class StorageException(AppException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "File storage is unavailable"
    error_code = "storage_error"
