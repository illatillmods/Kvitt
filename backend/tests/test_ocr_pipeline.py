import asyncio

from app.services.ocr import OCRClient, OCRLine, OCRBlock, OCRResult
from app.services.ocr_pipeline import ocr_result_to_text, run_ocr_pipeline


class FakeOCRClient:
    """Test double for OCRClient that simulates messy Swedish output.

    We intentionally include odd spacing and capitalization to ensure
    the flattening logic is robust and the parser downstream can still
    operate on the joined text.
    """

    async def extract(self, image_bytes: bytes) -> OCRResult:  # type: ignore[override]
        lines = [
            "   ICA   KVITTO   ",
            "2024-03-22    18:45",
            "red  bull   25,90",
            "OL  STARK 6-P   89,00",
            " SnUs   LM  52,00 ",
            "CHIPS     DILL  19,90  ",
            "  SUMMA    186, (??)  186,?",  # parser will ignore weird trailing tokens
            "SUMMA 186, (ignored) 186,?",
        ]
        blocks = [
            OCRBlock(lines=[OCRLine(text=line) for line in lines])
        ]
        raw_text = "\n".join(lines)
        return OCRResult(raw_text=raw_text, blocks=blocks, provider="fake-test", meta={})


def test_ocr_result_to_text_flattens_blocks_lines():
    lines = ["A", "B", "C"]
    blocks = [OCRBlock(lines=[OCRLine(text=line) for line in lines])]
    result = OCRResult(raw_text="", blocks=blocks, provider="test", meta={})

    flattened = ocr_result_to_text(result)
    assert flattened.splitlines() == lines


def test_run_ocr_pipeline_produces_parsed_receipt():
    client = FakeOCRClient()

    output = asyncio.run(run_ocr_pipeline(client, b"ignored"))

    assert output.ocr_result.provider == "fake-test"
    assert "ICA" in output.ocr_result.raw_text

    parsed = output.parsed_receipt
    assert parsed.merchant_name.startswith("ICA")
    assert len(parsed.line_items) >= 3
