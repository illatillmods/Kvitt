from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ParsedLineItemRecord(Base):
    """Raw parsed line item data before normalization.

    Mirrors :class:`app.services.parsing.ParsedLineItem` and stays immutable
    so we can always reconstruct what the parser saw.
    """

    __tablename__ = "parsed_line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    ocr_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ocr_results.id"), index=True
    )

    # Position of the line in the OCR'ed text, 0-based
    line_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    raw_description: Mapped[str] = mapped_column(String)
    original_line: Mapped[str] = mapped_column(String)

    quantity: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    confidence: Mapped[float] = mapped_column(Numeric(3, 2), default=0.5)
    notes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    ocr_result = relationship("OcrResultRecord", back_populates="parsed_line_items")
    normalized_line_items = relationship(
        "LineItem", back_populates="parsed_line_item"
    )
