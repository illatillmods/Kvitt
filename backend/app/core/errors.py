from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ReceiptProcessingError(Exception):
    message: str
    code: str
    stage: str
    status_code: int = 422
    retryable: bool = True
    suggestions: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return self.message