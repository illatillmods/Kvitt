from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.session import Base


class ProductStats(Base):
    """Aggregated per-product statistics.

    This table is optional and can be maintained by a background job.
    It exists to make product-level analytics queries efficient when
    history grows large.
    """

    __tablename__ = "product_stats"

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), primary_key=True
    )

    total_spend: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    purchase_count: Mapped[int] = mapped_column(Integer, default=0)
    first_purchase_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_purchase_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    product = relationship("Product", back_populates="stats")
