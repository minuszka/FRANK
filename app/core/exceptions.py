from typing import Any


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        code: str = "app_error",
        detail: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.detail = detail


class ExternalServiceError(AppError):
    def __init__(self, message: str, *, service: str, detail: Any | None = None) -> None:
        super().__init__(
            message,
            status_code=503,
            code=f"{service}_unavailable",
            detail=detail,
        )
        self.service = service


class InvalidPayloadError(AppError):
    def __init__(self, message: str, *, detail: Any | None = None) -> None:
        super().__init__(
            message,
            status_code=422,
            code="invalid_payload",
            detail=detail,
        )

