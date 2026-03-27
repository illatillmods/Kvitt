import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ReceiptIngestion(Base):
    """Top-level ingestion record for a receipt image or import.

    This keeps track of the raw source (image, import file, demo) and
    forms the root of the traceability chain:

    ReceiptIngestion -> OcrResultRecord -> ParsedLineItemRecord -> LineItem -> Product
    """

    __tablename__ = "receipt_ingestions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )

    # Where this ingestion came from: "upload", "demo", "import", etc.
    source: Mapped[str] = mapped_column(String(32))
    # High-level processing status: "pending", "processed", "failed".
    status: Mapped[str] = mapped_column(String(32), default="processed")

    original_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Storage key / path for the original image or import payload.
    storage_path: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    ocr_results = relationship(
        "OcrResultRecord", back_populates="ingestion", cascade="all, delete-orphan"
    )
    receipts = relationship(
        "Receipt", back_populates="ingestion", cascade="all, delete-orphan"
    )
