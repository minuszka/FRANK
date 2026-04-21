import asyncio
import copy
import json
import logging
import random
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings
from app.core.exceptions import AppError, ExternalServiceError
from app.core.utils import ensure_dir, utc_now_iso
from app.schemas.image import ImageGenerationRequest, ImageGenerationResult
from app.services.image_backend_base import ImageBackend

logger = logging.getLogger(__name__)


class ComfyUIService(ImageBackend):
    # TODO: Adjust these IDs if your local workflow uses different nodes.
    PROMPT_NODE_ID = "6"
    NEGATIVE_PROMPT_NODE_ID = "7"
    SAMPLER_NODE_ID = "3"
    LATENT_NODE_ID = "5"
    SAVE_NODE_ID = "9"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._timeout = httpx.Timeout(settings.comfyui_timeout_seconds)
        self._output_dir = ensure_dir(settings.output_dir)

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        workflow = self._load_workflow()
        applied_seed = request.seed if request.seed is not None else random.randint(0, 4294967295)
        prefix = f"imageagent_flux_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        self._apply_parameters(workflow, request, applied_seed, prefix)

        logger.info("Submitting ComfyUI prompt")
        prompt_id = await self._submit_prompt(workflow)
        history_record = await self._wait_for_completion(prompt_id)
        image_meta = self._extract_first_image(history_record)
        image_bytes = await self._download_image(image_meta)
        filename, file_path = self._save_image(
            image_bytes=image_bytes,
            prompt=request.prompt,
            desired_format=request.output_format,
        )

        return ImageGenerationResult(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            steps=request.steps,
            guidance=request.guidance,
            seed=applied_seed,
            output_format=request.output_format,
            filename=filename,
            file_path=str(file_path),
            image_url=f"/api/images/{filename}",
            created_at=utc_now_iso(),
            metadata={
                "prompt_id": prompt_id,
                "workflow_path": str(self.settings.workflow_path),
                "source_image_filename": image_meta.get("filename"),
                "source_image_subfolder": image_meta.get("subfolder"),
            },
        )

    def _load_workflow(self) -> dict[str, Any]:
        workflow_path = self.settings.workflow_path
        if not workflow_path.exists():
            raise AppError(
                f"Workflow file does not exist: {workflow_path}",
                status_code=500,
                code="workflow_missing",
            )
        with workflow_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        if not isinstance(payload, dict):
            raise AppError(
                "Workflow JSON must be an object.",
                status_code=500,
                code="workflow_invalid",
            )
        return copy.deepcopy(payload)

    def _apply_parameters(
        self,
        workflow: dict[str, Any],
        request: ImageGenerationRequest,
        seed: int,
        filename_prefix: str,
    ) -> None:
        self._set_node_input(workflow, self.PROMPT_NODE_ID, "text", request.prompt)
        self._set_node_input(
            workflow, self.NEGATIVE_PROMPT_NODE_ID, "text", request.negative_prompt
        )
        self._set_node_input(workflow, self.LATENT_NODE_ID, "width", request.width)
        self._set_node_input(workflow, self.LATENT_NODE_ID, "height", request.height)
        self._set_node_input(workflow, self.SAMPLER_NODE_ID, "steps", request.steps)
        self._set_node_input(workflow, self.SAMPLER_NODE_ID, "cfg", request.guidance)
        self._set_node_input(workflow, self.SAMPLER_NODE_ID, "seed", seed)
        self._set_node_input(workflow, self.SAVE_NODE_ID, "filename_prefix", filename_prefix)

    def _set_node_input(
        self, workflow: dict[str, Any], node_id: str, input_name: str, value: Any
    ) -> None:
        node = workflow.get(node_id)
        if not isinstance(node, dict):
            raise AppError(
                f"Workflow node {node_id} was not found.",
                status_code=500,
                code="workflow_node_missing",
            )
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            raise AppError(
                f"Workflow node {node_id} has invalid inputs.",
                status_code=500,
                code="workflow_node_invalid",
            )
        inputs[input_name] = value

    async def _submit_prompt(self, workflow: dict[str, Any]) -> str:
        url = f"{self.settings.comfyui_base_url}/prompt"
        payload = {"prompt": workflow, "client_id": str(uuid.uuid4())}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            logger.exception("Failed to submit prompt to ComfyUI")
            raise ExternalServiceError(
                "Failed to submit generation request to ComfyUI.",
                service="comfyui",
                detail=str(exc),
            ) from exc
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise ExternalServiceError(
                "ComfyUI did not return a prompt_id.",
                service="comfyui",
                detail=data,
            )
        return str(prompt_id)

    async def _wait_for_completion(self, prompt_id: str) -> dict[str, Any]:
        url = f"{self.settings.comfyui_base_url}/history/{prompt_id}"
        timeout_seconds = self.settings.comfyui_timeout_seconds
        deadline = datetime.now(UTC).timestamp() + timeout_seconds

        while datetime.now(UTC).timestamp() < deadline:
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    payload = response.json()
            except httpx.HTTPError as exc:
                logger.exception("Failed polling ComfyUI history")
                raise ExternalServiceError(
                    "Failed while polling ComfyUI generation status.",
                    service="comfyui",
                    detail=str(exc),
                ) from exc

            record = payload.get(prompt_id)
            if isinstance(record, dict) and record.get("outputs"):
                return record

            await asyncio.sleep(1.0)

        raise ExternalServiceError(
            "ComfyUI generation timed out.",
            service="comfyui",
            detail={"prompt_id": prompt_id, "timeout_seconds": timeout_seconds},
        )

    def _extract_first_image(self, history_record: dict[str, Any]) -> dict[str, Any]:
        outputs = history_record.get("outputs")
        if not isinstance(outputs, dict):
            raise ExternalServiceError(
                "ComfyUI response did not contain outputs.",
                service="comfyui",
                detail=history_record,
            )

        for node_output in outputs.values():
            if not isinstance(node_output, dict):
                continue
            images = node_output.get("images")
            if isinstance(images, list) and images:
                first = images[0]
                if isinstance(first, dict) and first.get("filename"):
                    return first

        raise ExternalServiceError(
            "No generated image was found in ComfyUI outputs.",
            service="comfyui",
            detail=history_record,
        )

    async def _download_image(self, image_meta: dict[str, Any]) -> bytes:
        params = {
            "filename": image_meta.get("filename"),
            "subfolder": image_meta.get("subfolder", ""),
            "type": image_meta.get("type", "output"),
        }
        url = f"{self.settings.comfyui_base_url}/view"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as exc:
            logger.exception("Failed to download generated image from ComfyUI")
            raise ExternalServiceError(
                "Failed to download generated image from ComfyUI.",
                service="comfyui",
                detail=str(exc),
            ) from exc

    def _save_image(self, image_bytes: bytes, prompt: str, desired_format: str) -> tuple[str, Path]:
        extension = self._normalize_extension(desired_format)
        slug = self._slugify(prompt)[:40] or "image"
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{slug}.{extension}"
        file_path = self._output_dir / filename
        file_path.write_bytes(image_bytes)
        return filename, file_path

    @staticmethod
    def _normalize_extension(value: str) -> str:
        cleaned = value.lower().replace("jpeg", "jpg")
        if cleaned not in {"png", "jpg", "webp"}:
            return "png"
        return cleaned

    @staticmethod
    def _slugify(text: str) -> str:
        lowered = text.lower()
        slug = re.sub(r"[^a-z0-9]+", "_", lowered)
        return slug.strip("_")

