from datetime import datetime

import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.session import Base
from app.db.types import GUID


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("receipts.id"), index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), nullable=True, index=True
    )
    parsed_line_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("parsed_line_items.id"), nullable=True, index=True
    )

    raw_description: Mapped[str] = mapped_column(String)
    quantity: Mapped[float] = mapped_column(Numeric(10, 3), default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    total_price: Mapped[float] = mapped_column(Numeric(10, 2))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    receipt = relationship("Receipt", back_populates="line_items")
    product = relationship("Product")
    parsed_line_item = relationship("ParsedLineItemRecord", back_populates="normalized_line_items")
