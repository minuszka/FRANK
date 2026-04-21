import re

from app.schemas.chat import RoutedTask, TaskType


class RouterService:
    IMAGE_PATTERNS = (
        r"\bgener[aá]lj\s+k[eé]pet\b",
        r"\bk[eé]sz[ií]ts\s+k[eé]pet\b",
        r"\brajzolj\b",
        r"\billusztr[aá]ci[oó]\b",
        r"\blog[oó]\b",
        r"\bposter\b",
        r"\bplak[aá]t\b",
        r"\bimage\b",
        r"\bpicture\b",
        r"\brender\b",
        r"\bconcept art\b",
        r"\bportrait\b",
    )

    CODE_PATTERNS = (
        r"\bpython\b",
        r"\bjavascript\b",
        r"\btypescript\b",
        r"\bbash\b",
        r"\bshell\b",
        r"\bscript\b",
        r"\bk[oó]d\b",
        r"\bprogram\b",
        r"\balgoritmus\b",
        r"\bdebug\b",
        r"\bbug\b",
        r"\bsql\b",
        r"\bregex\b",
        r"\bapi\b",
    )

    def route(self, message: str) -> RoutedTask:
        normalized = message.lower().strip()

        for pattern in self.IMAGE_PATTERNS:
            if re.search(pattern, normalized):
                return RoutedTask(
                    task_type=TaskType.image,
                    reason=f"Matched image keyword pattern: {pattern}",
                )

        for pattern in self.CODE_PATTERNS:
            if re.search(pattern, normalized):
                return RoutedTask(
                    task_type=TaskType.code,
                    reason=f"Matched code keyword pattern: {pattern}",
                )

        return RoutedTask(task_type=TaskType.chat, reason="Defaulted to chat category")

