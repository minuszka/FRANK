import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.config import Settings
from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class OllamaService:
    def __init__(self, settings: Settings, image_prompt_template: str) -> None:
        self.settings = settings
        self.image_prompt_template = image_prompt_template
        self._timeout = httpx.Timeout(settings.ollama_timeout_seconds)

    async def chat(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.settings.ollama_model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.settings.ollama_keep_alive,
        }
        data = await self._chat_request(payload)
        message = data.get("message", {})
        return str(message.get("content", "")).strip()

    async def stream_chat(
        self, messages: list[dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.settings.ollama_model,
            "messages": messages,
            "stream": True,
            "keep_alive": self.settings.ollama_keep_alive,
        }
        url = f"{self.settings.ollama_base_url}/api/chat"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        item = json.loads(line)
                        if item.get("done"):
                            break
                        token = item.get("message", {}).get("content")
                        if token:
                            yield token
        except httpx.HTTPError as exc:
            logger.exception("Ollama streaming request failed")
            raise ExternalServiceError(
                "Failed to stream response from Ollama.",
                service="ollama",
                detail=str(exc),
            ) from exc

    async def generate_image_json(
        self,
        user_message: str,
        defaults: dict[str, Any],
    ) -> str:
        prompt = self.image_prompt_template.format(
            default_width=defaults["width"],
            default_height=defaults["height"],
            default_steps=defaults["steps"],
            default_guidance=defaults["guidance"],
            default_negative_prompt=defaults["negative_prompt"],
        )
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message},
        ]
        return await self.chat(messages)

    async def _chat_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.settings.ollama_base_url}/api/chat"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            logger.exception("Ollama request failed")
            raise ExternalServiceError(
                "Failed to communicate with Ollama.",
                service="ollama",
                detail=str(exc),
            ) from exc
