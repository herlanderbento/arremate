from typing import Any


class DomainError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class EntityValidationException(Exception):
    def __init__(self, errors: str = "Entity validation error occurred."):
        super().__init__(errors)


class NotFoundException(Exception):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


class ConflictException(Exception):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


class ForbiddenException(Exception):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


class InvalidArgumentException(Exception):
    def __init__(self, message):
        super().__init__(message)


class UnauthorizedException(Exception):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


class InvalidUuidException(Exception):
    def __init__(self, uuid: str):
        super().__init__(f"ID {uuid} must be a valid UUID")


class GatewayException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
