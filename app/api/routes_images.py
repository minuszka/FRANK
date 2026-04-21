import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.config import Settings, get_settings
from app.core.utils import safe_join
from app.schemas.image import ImageGenerationRequest, ImageGenerationResult
from app.services.comfyui_service import ComfyUIService
from app.dependencies import get_comfyui_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["images"])


@router.post("/api/generate-image", response_model=ImageGenerationResult)
async def generate_image(
    payload: ImageGenerationRequest,
    comfy_service: ComfyUIService = Depends(get_comfyui_service),
) -> ImageGenerationResult:
    logger.info("POST /api/generate-image")
    return await comfy_service.generate(payload)


@router.get("/api/images/{filename}")
async def get_generated_image(
    filename: str,
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    candidate = safe_join(Path(settings.output_dir), filename)
    if candidate is None or not candidate.exists():
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(candidate)

