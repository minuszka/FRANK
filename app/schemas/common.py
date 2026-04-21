from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    code: str | None = None


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str

