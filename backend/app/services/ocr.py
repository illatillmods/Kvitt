from dataclasses import dataclass, field
from typing import Any, List, Optional, Protocol


@dataclass
class BoundingBox:
    """Simple axis-aligned bounding box.

    Units are provider-defined (usually pixels). We only need this
    for debugging and potential later spatial reasoning.
    """

    x: int
    y: int
    width: int
    height: int


@dataclass
class OCRWord:
    text: str
    confidence: Optional[float] = None
    bbox: Optional[BoundingBox] = None


@dataclass
class OCRLine:
    text: str
    words: List[OCRWord] = field(default_factory=list)
    bbox: Optional[BoundingBox] = None


@dataclass
class OCRBlock:
    lines: List[OCRLine] = field(default_factory=list)
    bbox: Optional[BoundingBox] = None


@dataclass
class OCRResult:
    """Provider-agnostic OCR output.

    - raw_text: concatenated text, primarily for storage / debugging
    - blocks: structured text blocks with line candidates
    - provider: identifier for the OCR backend
    - meta: unstructured provider-specific diagnostics
    """

    raw_text: str
    blocks: List[OCRBlock]
    provider: str
    meta: dict[str, Any] = field(default_factory=dict)


class OCRClient(Protocol):
    async def extract(self, image_bytes: bytes) -> OCRResult:  # pragma: no cover - interface only
        ...


class DummyOCRClient:
    """Placeholder OCR client for early development.

    Returns hard-coded Swedish-style receipt text so we can build
    parsing, normalization, and UI flows before wiring real OCR.
    """

    provider_name = "dummy"

    async def extract(self, image_bytes: bytes) -> OCRResult:
        # Example: simple ICA-style snippet in Swedish with a
        # realistic line-level structure.
        lines = [
            "ICA KVITTO",
            "2024-03-22 18:45",
            "Red Bull 25,90",
            "OL STARK 6-P 89,00",
            "CHIPS DILL 19,90",
            "SUMMA 134,80",
        ]
        blocks = [
            OCRBlock(
                lines=[OCRLine(text=line, words=[OCRWord(text=line)]) for line in lines]
            )
        ]
        raw_text = "\n".join(lines)
        return OCRResult(
            raw_text=raw_text,
            blocks=blocks,
            provider=self.provider_name,
            meta={"note": "dummy-ocr"},
        )
