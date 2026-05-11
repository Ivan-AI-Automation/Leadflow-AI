from typing import Any, cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "app_error",
        details: Any | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "The requested resource was not found.") -> None:
        super().__init__(
            message,
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
        )


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_409_CONFLICT,
            code="conflict",
        )


class AuthenticationError(AppError):
    def __init__(self, message: str = "Invalid authentication credentials.") -> None:
        super().__init__(
            message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="authentication_error",
        )


class ValidationError(AppError):
    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="validation_error",
            details=details,
        )


class FileTooLargeError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            code="file_too_large",
        )


class AIProviderError(AppError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        code: str = "ai_provider_error",
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            code=code,
        )


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def http_error_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    message = str(exc.detail) if exc.detail else "The requested operation failed."
    return error_response(
        status_code=exc.status_code,
        code="http_error",
        message=message,
    )


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="request_validation_error",
        message="The request data is invalid. Please check the submitted fields.",
        details=exc.errors(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_server_error",
        message="An unexpected server error occurred. Please try again later.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, cast(Any, app_error_handler))
    app.add_exception_handler(StarletteHTTPException, cast(Any, http_error_handler))
    app.add_exception_handler(RequestValidationError, cast(Any, request_validation_error_handler))
    app.add_exception_handler(Exception, cast(Any, unhandled_exception_handler))
