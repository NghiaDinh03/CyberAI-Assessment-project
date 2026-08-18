"""Custom exception classes for the CyberAI Assessment Platform.

All exceptions carry a user-safe ``message`` and an HTTP ``status_code``.
Internal details (stack traces, file paths, variable dumps) are NEVER
forwarded to API consumers — the global handlers in ``main.py`` enforce this.
"""

from typing import Any, Optional


class AppException(Exception):
    """Base application exception.

    Attributes:
        message     -- User-safe error description (shown in API response).
        status_code -- HTTP status code to return (default 500).
        details     -- Optional structured payload.  Must contain only
                       safe, non-sensitive data; never include raw exception
                       messages, file paths, or stack traces here.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class ModelNotLoadedError(AppException):
    """Raised when the requested AI model is unavailable or not yet loaded."""

    def __init__(self, message: str = "AI model is not available", details: Optional[Any] = None) -> None:
        super().__init__(message=message, status_code=503, details=details)


class VectorStoreError(AppException):
    """Raised when a ChromaDB / vector store operation fails."""

    def __init__(self, message: str = "Vector store operation failed", details: Optional[Any] = None) -> None:
        super().__init__(message=message, status_code=503, details=details)


class ValidationError(AppException):
    """Raised for business-logic validation failures (not Pydantic schema errors)."""

    def __init__(self, message: str = "Validation error", details: Optional[Any] = None) -> None:
        super().__init__(message=message, status_code=422, details=details)


class NotFoundError(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None) -> None:
        super().__init__(message=message, status_code=404, details=details)


class AuthorizationError(AppException):
    """Raised when a request lacks sufficient permissions."""

    def __init__(self, message: str = "Unauthorized", details: Optional[Any] = None) -> None:
        super().__init__(message=message, status_code=403, details=details)
