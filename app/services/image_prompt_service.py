import json
import logging
from typing import Any

from pydantic import ValidationError

from app.config import Settings
from app.core.utils import extract_first_json_object
from app.schemas.image import ImageGenerationRequest
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)


def parse_image_json(raw_text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return extract_first_json_object(raw_text)


def normalize_image_payload(
    payload: dict[str, Any] | None,
    defaults: dict[str, Any],
    user_message: str,
) -> dict[str, Any]:
    merged = dict(defaults)
    if payload:
        merged.update(payload)

    merged["action"] = "generate_image"
    merged["prompt"] = str(merged.get("prompt") or user_message).strip()
    merged["negative_prompt"] = str(
        merged.get("negative_prompt") or defaults["negative_prompt"]
    ).strip()
    merged["output_format"] = str(merged.get("output_format") or "png").lower()

    merged["width"] = _clamp_int(merged.get("width"), 256, 2048, defaults["width"])
    merged["height"] = _clamp_int(merged.get("height"), 256, 2048, defaults["height"])
    merged["steps"] = _clamp_int(merged.get("steps"), 1, 120, defaults["steps"])
    merged["guidance"] = _clamp_float(
        merged.get("guidance"), 1.0, 20.0, defaults["guidance"]
    )

    seed = merged.get("seed")
    if seed is None or seed == "":
        merged["seed"] = None
    else:
        merged["seed"] = _clamp_int(seed, 0, 4294967295, None)

    merged["style_hint"] = _to_optional_str(merged.get("style_hint"))
    return merged


def _to_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clamp_int(value: Any, minimum: int, maximum: int, default: int | None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        if default is None:
            return minimum
        parsed = default
    parsed = max(minimum, min(maximum, parsed))
    if minimum >= 8:
        parsed = (parsed // 8) * 8
    return parsed


def _clamp_float(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


class ImagePromptService:
    def __init__(self, settings: Settings, ollama_service: OllamaService) -> None:
        self.settings = settings
        self.ollama_service = ollama_service

    def defaults(self) -> dict[str, Any]:
        return {
            "width": self.settings.default_image_width,
            "height": self.settings.default_image_height,
            "steps": self.settings.default_image_steps,
            "guidance": self.settings.default_image_guidance,
            "negative_prompt": self.settings.default_negative_prompt,
            "output_format": "png",
        }

    async def extract_request(self, user_message: str) -> ImageGenerationRequest:
        defaults = self.defaults()
        raw_output = await self.ollama_service.generate_image_json(user_message, defaults)
        logger.debug("Raw image JSON output from model: %s", raw_output)

        parsed = parse_image_json(raw_output)
        normalized = normalize_image_payload(parsed, defaults, user_message)

        try:
            return ImageGenerationRequest.model_validate(normalized)
        except ValidationError:
            logger.exception("Image prompt validation failed, applying strict fallback.")
            fallback = normalize_image_payload({}, defaults, user_message)
            return ImageGenerationRequest.model_validate(fallback)

