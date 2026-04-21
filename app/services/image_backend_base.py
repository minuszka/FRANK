from abc import ABC, abstractmethod

from app.schemas.image import ImageGenerationRequest, ImageGenerationResult


class ImageBackend(ABC):
    @abstractmethod
    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        raise NotImplementedError

