import json
import logging
from collections.abc import AsyncGenerator

from app.core.utils import utc_now_iso
from app.schemas.chat import ChatRequest, ChatResponse, TaskType
from app.schemas.image import ImageGenerationRequest
from app.services.history_service import HistoryService
from app.services.image_backend_base import ImageBackend
from app.services.image_prompt_service import ImagePromptService
from app.services.ollama_service import OllamaService
from app.services.router_service import RouterService

logger = logging.getLogger(__name__)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class ChatService:
    def __init__(
        self,
        router_service: RouterService,
        ollama_service: OllamaService,
        image_prompt_service: ImagePromptService,
        image_backend: ImageBackend,
        history_service: HistoryService,
    ) -> None:
        self.router_service = router_service
        self.ollama_service = ollama_service
        self.image_prompt_service = image_prompt_service
        self.image_backend = image_backend
        self.history_service = history_service

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        route = self.router_service.route(request.message)
        logger.info("Routing decision: %s | reason=%s", route.task_type, route.reason)

        self.history_service.append(request.session_id, "user", request.message)

        if route.task_type == TaskType.image:
            image_request = await self.image_prompt_service.extract_request(request.message)
            image_result = await self.image_backend.generate(image_request)
            assistant_text = "Image generation complete. You can open the preview in the chat."
            self.history_service.append(
                request.session_id,
                "assistant",
                assistant_text,
                metadata={"image_url": image_result.image_url},
            )
            return ChatResponse(
                session_id=request.session_id,
                task_type=route.task_type,
                route_reason=route.reason,
                message=assistant_text,
                image=image_result,
                created_at=utc_now_iso(),
            )

        messages = self._build_messages_for_ollama(request.session_id, route.task_type)
        assistant_text = await self.ollama_service.chat(messages)
        self.history_service.append(request.session_id, "assistant", assistant_text)

        return ChatResponse(
            session_id=request.session_id,
            task_type=route.task_type,
            route_reason=route.reason,
            message=assistant_text,
            created_at=utc_now_iso(),
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        route = self.router_service.route(request.message)
        logger.info("Streaming routing decision: %s | reason=%s", route.task_type, route.reason)
        self.history_service.append(request.session_id, "user", request.message)

        yield _sse(
            "meta",
            {
                "session_id": request.session_id,
                "task_type": route.task_type.value,
                "route_reason": route.reason,
            },
        )

        if route.task_type == TaskType.image:
            image_request: ImageGenerationRequest = await self.image_prompt_service.extract_request(
                request.message
            )
            image_result = await self.image_backend.generate(image_request)
            assistant_text = "Image generation complete. Preview is attached."
            self.history_service.append(
                request.session_id,
                "assistant",
                assistant_text,
                metadata={"image_url": image_result.image_url},
            )
            yield _sse(
                "done",
                {
                    "message": assistant_text,
                    "image": image_result.model_dump(),
                    "created_at": utc_now_iso(),
                },
            )
            return

        messages = self._build_messages_for_ollama(request.session_id, route.task_type)
        chunks: list[str] = []
        async for chunk in self.ollama_service.stream_chat(messages):
            chunks.append(chunk)
            yield _sse("token", {"content": chunk})

        assistant_text = "".join(chunks).strip()
        self.history_service.append(request.session_id, "assistant", assistant_text)
        yield _sse(
            "done",
            {"message": assistant_text, "image": None, "created_at": utc_now_iso()},
        )

    def _build_messages_for_ollama(
        self, session_id: str, task_type: TaskType
    ) -> list[dict[str, str]]:
        history = self.history_service.get(session_id)
        context_limit = max(2, self.ollama_service.settings.history_context_messages)
        max_chars = max(200, self.ollama_service.settings.history_max_message_chars)
        history = history[-context_limit:]
        if task_type == TaskType.code:
            system_message = (
                "You are a pragmatic senior software engineer. "
                "Give clear, actionable answers with concise code examples when useful."
            )
        else:
            system_message = (
                "You are a helpful local assistant. Keep answers clear and practical."
            )

        messages: list[dict[str, str]] = [{"role": "system", "content": system_message}]
        for item in history:
            if item.role in {"user", "assistant"}:
                content = item.content
                if len(content) > max_chars:
                    content = content[: max_chars - 3] + "..."
                messages.append({"role": item.role, "content": content})
        return messages
