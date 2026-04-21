from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "images"
DEFAULT_WORKFLOW_PATH = PROJECT_ROOT / "app" / "workflows" / "flux_dev_workflow.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ImageAgent"
    app_version: str = "0.1.0"

    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434", validation_alias="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(
        default="huihui_ai/qwen3-coder-next-abliterated", validation_alias="OLLAMA_MODEL"
    )

    comfyui_base_url: str = Field(
        default="http://127.0.0.1:8188", validation_alias="COMFYUI_BASE_URL"
    )
    workflow_path: Path = Field(
        default=DEFAULT_WORKFLOW_PATH, validation_alias="WORKFLOW_PATH"
    )

    output_dir: Path = Field(default=DEFAULT_OUTPUT_PATH, validation_alias="OUTPUT_DIR")

    app_host: str = Field(default="127.0.0.1", validation_alias="APP_HOST")
    app_port: int = Field(default=8000, validation_alias="APP_PORT")

    default_image_width: int = Field(default=1024, validation_alias="DEFAULT_IMAGE_WIDTH")
    default_image_height: int = Field(default=1024, validation_alias="DEFAULT_IMAGE_HEIGHT")
    default_image_steps: int = Field(default=28, validation_alias="DEFAULT_IMAGE_STEPS")
    default_image_guidance: float = Field(
        default=4.0, validation_alias="DEFAULT_IMAGE_GUIDANCE"
    )
    default_negative_prompt: str = Field(
        default="blurry, low quality, text, watermark, distorted anatomy",
        validation_alias="DEFAULT_NEGATIVE_PROMPT",
    )

    ollama_timeout_seconds: int = Field(default=120, validation_alias="OLLAMA_TIMEOUT_SECONDS")
    comfyui_timeout_seconds: int = Field(
        default=300, validation_alias="COMFYUI_TIMEOUT_SECONDS"
    )

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    @field_validator("ollama_base_url", "comfyui_base_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("output_dir", "workflow_path")
    @classmethod
    def resolve_path(cls, value: Path) -> Path:
        return value.expanduser().resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()

