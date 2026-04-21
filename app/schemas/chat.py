from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.image import ImageGenerationResult


class TaskType(str, Enum):
    chat = "chat"
    code = "code"
    image = "image"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="default", max_length=128)
    stream: bool = False


class RoutedTask(BaseModel):
    task_type: TaskType
    reason: str


class ChatResponse(BaseModel):
    session_id: str
    task_type: TaskType
    route_reason: str
    message: str
    image: ImageGenerationResult | None = None
    created_at: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]


class HistoryDeleteResponse(BaseModel):
    session_id: str
    deleted: bool

