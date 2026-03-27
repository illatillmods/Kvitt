import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.session import Base
from app.db.types import GUID


class HabitInsightSnapshot(Base):
    """Snapshot of computed habit insights for a user over a time window.

    Current MVP insights are computed on the fly, but this table allows
    us to persist selected snapshots if needed for longitudinal analysis
    or debugging.
    """

    __tablename__ = "habit_insight_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True, index=True
    )

    label: Mapped[str] = mapped_column(String)
    monthly_cost_estimate: Mapped[float] = mapped_column(Numeric(12, 2))
    frequency_per_month: Mapped[float] = mapped_column(Numeric(10, 2))

    period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
