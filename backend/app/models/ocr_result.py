import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OcrResultRecord(Base):
    """Persistent OCR output linked to an ingestion.

    Stores the raw OCR text and structured blocks/metadata where available.
    """

    __tablename__ = "ocr_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    ingestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("receipt_ingestions.id"), index=True
    )

    provider: Mapped[str] = mapped_column(String(64))
    raw_text: Mapped[str] = mapped_column(String)
    blocks: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    ingestion = relationship("ReceiptIngestion", back_populates="ocr_results")
    parsed_line_items = relationship(
        "ParsedLineItemRecord",
        back_populates="ocr_result",
        cascade="all, delete-orphan",
    )
