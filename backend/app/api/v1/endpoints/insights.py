from datetime import timedelta, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.analytics import InsightsSummary
from app.services.insights import compute_insights_summary

router = APIRouter()


@router.get("/summary", response_model=InsightsSummary)
async def insights_summary(
    days: int = Query(default=30, ge=7, le=180, description="Look back this many days"),
    db: Session = Depends(get_db_session),
) -> InsightsSummary:
    """Return a compact insights summary for the last N days.

    For MVP we compute insights globally (no per-user partitioning yet).
    """

    return compute_insights_summary(db, period_days=days)
