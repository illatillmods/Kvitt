from dataclasses import dataclass

from app.services.ocr import OCRClient, OCRResult
from app.services.parsing import ParsedReceipt, parse_receipt_text


@dataclass
class OCRPipelineOutput:
    """Result of running OCR + text extraction + parsing.

    This is kept internal to the backend so we can iterate on
    parsing while keeping the external API stable.
    """

    ocr_result: OCRResult
    parsed_receipt: ParsedReceipt


def ocr_result_to_text(ocr_result: OCRResult) -> str:
    """Flatten OCR blocks/lines into a single text blob.

    This function defines the contract between OCR output and the
    text-based parser. Keeping it here makes the boundary explicit
    and easy to test.
    """

    lines: list[str] = []
    for block in ocr_result.blocks:
        for line in block.lines:
            # Use the line text as-is; the parser will handle
            # trimming, spacing, and Swedish-specific quirks.
            if line.text is not None:
                lines.append(line.text)
    if not lines:
        return ocr_result.raw_text
    return "\n".join(lines)


async def run_ocr_pipeline(ocr_client: OCRClient, image_bytes: bytes) -> OCRPipelineOutput:
    """Run OCR and parse the resulting text into a ParsedReceipt.

    - Keeps OCR concerns separate from parsing
    - Central place to add logging / tracing in the future
    """

    ocr_result = await ocr_client.extract(image_bytes)
    text_for_parser = ocr_result_to_text(ocr_result) or ocr_result.raw_text
    parsed = parse_receipt_text(text_for_parser)
    return OCRPipelineOutput(ocr_result=ocr_result, parsed_receipt=parsed)
