from functools import lru_cache
from pathlib import Path

from app.config import Settings, get_settings
from app.services.chat_service import ChatService
from app.services.comfyui_service import ComfyUIService
from app.services.history_service import HistoryService
from app.services.image_prompt_service import ImagePromptService
from app.services.ollama_service import OllamaService
from app.services.router_service import RouterService


def _load_prompt_file(filename: str) -> str:
    path = Path(__file__).resolve().parent / "prompts" / filename
    return path.read_text(encoding="utf-8")


@lru_cache
def get_router_service() -> RouterService:
    return RouterService()


@lru_cache
def get_history_service() -> HistoryService:
    return HistoryService(max_messages_per_session=50)


@lru_cache
def get_ollama_service() -> OllamaService:
    settings: Settings = get_settings()
    image_prompt_template = _load_prompt_file("image_prompt_instruction.txt")
    return OllamaService(settings=settings, image_prompt_template=image_prompt_template)


@lru_cache
def get_image_prompt_service() -> ImagePromptService:
    settings: Settings = get_settings()
    return ImagePromptService(settings=settings, ollama_service=get_ollama_service())


@lru_cache
def get_comfyui_service() -> ComfyUIService:
    settings: Settings = get_settings()
    return ComfyUIService(settings=settings)


@lru_cache
def get_chat_service() -> ChatService:
    return ChatService(
        router_service=get_router_service(),
        ollama_service=get_ollama_service(),
        image_prompt_service=get_image_prompt_service(),
        image_backend=get_comfyui_service(),
        history_service=get_history_service(),
    )

