import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from shared.domain.exceptions import (
    ConflictException,
    DomainError,
    EntityValidationException,
    ForbiddenException,
    GatewayException,
    InvalidArgumentException,
    InvalidUuidException,
    NotFoundException,
    UnauthorizedException,
)
from shared.infra.api.money import to_json

logger = logging.getLogger(__name__)


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": to_json(details or {})}}


def _error_response(status_code: int, code: str, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=error_body(code, str(exc)))


def _validation_message(error_type: str, field: str) -> str:
    messages = {
        "missing": f"The field '{field}' is required.",
        "string_too_short": f"The field '{field}' cannot be empty.",
        "string_type": f"The field '{field}' must be a string.",
        "bool_parsing": f"The field '{field}' must be true or false.",
        "bool_type": f"The field '{field}' must be true or false.",
    }
    return messages.get(error_type, f"The field '{field}' is invalid.")


# Exception class -> (HTTP status, default error code). DomainError carries its own code;
# the others may override the default through an optional `code` attribute.
_SIMPLE_HANDLERS: list[tuple[type[Exception], int, str]] = [
    (NotFoundException, 404, "NOT_FOUND"),
    (ConflictException, 409, "CONFLICT"),
    (ForbiddenException, 403, "FORBIDDEN"),
    (UnauthorizedException, 401, "UNAUTHORIZED"),
    (GatewayException, 503, "EXTERNAL_UNAVAILABLE"),
    (EntityValidationException, 422, "VALIDATION_ERROR"),
    (InvalidArgumentException, 422, "INVALID_ARGUMENT"),
    (InvalidUuidException, 422, "INVALID_ID"),
]


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(_request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            location = [str(part) for part in error["loc"] if part != "body"]
            field = location[-1] if location else "body"
            errors.append(
                {
                    "field": ".".join(location),
                    "message": _validation_message(error["type"], field),
                }
            )
        return JSONResponse(
            status_code=422,
            content=error_body("VALIDATION_ERROR", "Invalid data.", {"fields": errors}),
        )

    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError):
        return JSONResponse(status_code=422, content=error_body(exc.code, exc.message, exc.details))

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_request: Request, exc: Exception):
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=error_body("INTERNAL_ERROR", "Unexpected error."),
        )

    for exc_class, status_code, code in _SIMPLE_HANDLERS:

        async def handler(_request: Request, exc: Exception, status_code=status_code, code=code):
            return _error_response(status_code, getattr(exc, "code", None) or code, exc)

        app.add_exception_handler(exc_class, handler)
