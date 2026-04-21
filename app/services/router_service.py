import re

from app.schemas.chat import RoutedTask, TaskType


class RouterService:
    IMAGE_STRONG_TERMS = {
        "logo",
        "poster",
        "plakat",
        "illusztracio",
        "illustracio",
        "portrait",
        "portre",
        "render",
        "fanart",
        "wallpaper",
    }
    IMAGE_VERBS = {
        "generalj",
        "generald",
        "general",
        "keszits",
        "keszit",
        "csinalj",
        "rajzolj",
        "alkoss",
        "letrehoz",
        "create",
        "generate",
        "draw",
        "make",
        "render",
    }
    IMAGE_NOUNS = {
        "kep",
        "kepet",
        "image",
        "picture",
        "illustracio",
        "illusztracio",
        "logo",
        "poster",
        "plakat",
        "portre",
        "portrait",
    }
    IMAGE_REQUEST_WORDS = {
        "kerek",
        "kernek",
        "kerem",
        "szeretnek",
        "akarok",
        "kellene",
        "legyszives",
        "pls",
        "please",
    }
    IMAGE_STYLE_HINTS = {
        "anime",
        "cinematic",
        "realistic",
        "realisztikus",
        "foto",
        "photorealistic",
        "sexy",
    }
    CODE_TERMS = {
        "python",
        "javascript",
        "typescript",
        "bash",
        "shell",
        "script",
        "kod",
        "program",
        "algoritmus",
        "debug",
        "bug",
        "sql",
        "regex",
        "api",
    }

    @staticmethod
    def _normalize(message: str) -> str:
        lowered = message.lower()
        translated = lowered.translate(
            str.maketrans("áéíóöőúüű", "aeiooouuu")
        )
        cleaned = re.sub(r"[^a-z0-9\s]", " ", translated)
        return re.sub(r"\s+", " ", cleaned).strip()

    def route(self, message: str) -> RoutedTask:
        normalized = self._normalize(message)
        tokens = set(normalized.split())

        for term in self.IMAGE_STRONG_TERMS:
            if term in normalized:
                return RoutedTask(
                    task_type=TaskType.image,
                    reason=f"Matched strong image term: {term}",
                )

        if tokens.intersection(self.IMAGE_VERBS) and tokens.intersection(self.IMAGE_NOUNS):
            return RoutedTask(
                task_type=TaskType.image,
                reason="Matched image verb + image noun combination",
            )

        if tokens.intersection(self.IMAGE_REQUEST_WORDS) and tokens.intersection(
            self.IMAGE_NOUNS
        ):
            return RoutedTask(
                task_type=TaskType.image,
                reason="Matched image request word + image noun combination",
            )

        # Fallback: if the user clearly asks for an image noun + style hint,
        # treat it as image generation even when phrasing is unusual.
        if tokens.intersection(self.IMAGE_NOUNS) and tokens.intersection(self.IMAGE_STYLE_HINTS):
            return RoutedTask(
                task_type=TaskType.image,
                reason="Matched image noun + style hint fallback",
            )

        code_hits = sorted(tokens.intersection(self.CODE_TERMS))
        if code_hits:
            return RoutedTask(
                task_type=TaskType.code,
                reason=f"Matched code term(s): {', '.join(code_hits[:3])}",
            )

        return RoutedTask(task_type=TaskType.chat, reason="Defaulted to chat category")
