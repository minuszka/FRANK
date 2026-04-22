import logging
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.dependencies import get_chat_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.get("/api/config")
async def get_public_config(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "ollama_base_url": settings.ollama_base_url,
        "ollama_model": settings.ollama_model,
        "comfyui_base_url": settings.comfyui_base_url,
        "default_image_width": settings.default_image_width,
        "default_image_height": settings.default_image_height,
        "default_image_steps": settings.default_image_steps,
        "default_image_guidance": settings.default_image_guidance,
        "output_dir": str(settings.output_dir),
        "ollama_keep_alive": settings.ollama_keep_alive,
        "history_context_messages": settings.history_context_messages,
        "history_max_message_chars": settings.history_max_message_chars,
    }


@router.post("/api/chat", response_model=ChatResponse)
async def post_chat(
    payload: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    logger.info("POST /api/chat session=%s", payload.session_id)
    return await chat_service.handle_chat(payload)


@router.post("/api/chat/stream")
async def post_chat_stream(
    payload: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    logger.info("POST /api/chat/stream session=%s", payload.session_id)
    generator = chat_service.stream_chat(payload)
    return StreamingResponse(generator, media_type="text/event-stream")
