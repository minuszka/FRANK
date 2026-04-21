from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ImageGenerationRequest(BaseModel):
    action: Literal["generate_image"] = "generate_image"
    prompt: str = Field(min_length=3, max_length=4000)
    negative_prompt: str = Field(
        default="blurry, low quality, text, watermark, distorted anatomy"
    )
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)
    steps: int = Field(default=28, ge=1, le=120)
    guidance: float = Field(default=4.0, ge=1.0, le=20.0)
    seed: int | None = Field(default=None, ge=0, le=4294967295)
    style_hint: str | None = None
    output_format: Literal["png", "jpg", "jpeg", "webp"] = "png"

    @field_validator("width", "height")
    @classmethod
    def must_be_multiple_of_8(cls, value: int) -> int:
        rounded = max(256, min(2048, (value // 8) * 8))
        return rounded or 512


class ImageGenerationResult(BaseModel):
    task: Literal["generate_image"] = "generate_image"
    prompt: str
    negative_prompt: str
    width: int
    height: int
    steps: int
    guidance: float
    seed: int
    output_format: str
    filename: str
    file_path: str
    image_url: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)

