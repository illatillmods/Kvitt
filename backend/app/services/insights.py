from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.access import (
    FEATURE_ADVANCED_HABIT_INSIGHTS,
    FEATURE_BASIC_STATISTICS,
    FEATURE_DEEPER_TRENDS,
    AccessContext,
)
from app.core.time import utc_now
from app.models.line_item import LineItem
from app.models.product import Product
from app.models.receipt import Receipt
from app.schemas.access import AccessSnapshot
from app.schemas.analytics import (
    HabitInsightOut,
    InsightHighlight,
    InsightsSummary,
    ProductInsight,
    TimeBucketInsight,
)


@dataclass
class _HabitConfig:
    label: str
    categories: Tuple[str, ...]


_HABITS: Tuple[_HabitConfig, ...] = (
    _HabitConfig(label="Beer", categories=("beer",)),
    _HabitConfig(label="Coffee", categories=("coffee", "cafe")),
    _HabitConfig(label="Snacks", categories=("snacks", "candy")),
    _HabitConfig(label="Energy drinks", categories=("energy_drink",)),
)


def _load_line_items_for_period(
    db: Session, start: datetime, end: datetime
) -> Iterable[tuple[LineItem, Product | None, Receipt | None]]:
    stmt = (
        select(LineItem, Product, Receipt)
        .join(Receipt, LineItem.receipt_id == Receipt.id)
        .outerjoin(Product, LineItem.product_id == Product.id)
        .where(Receipt.purchase_datetime >= start, Receipt.purchase_datetime < end)
    )
    for li, product, receipt in db.execute(stmt).all():
        yield li, product, receipt


def compute_insights_summary(db: Session, period_days: int = 30) -> InsightsSummary:
    """Compute a compact insights summary over the last ``period_days`` days.

    For MVP this is global (no per-user partitioning yet).
    """

    now = utc_now()
    start = now - timedelta(days=period_days)

    # Load all relevant line items for the period
    rows = list(_load_line_items_for_period(db, start=start, end=now))

    # Per-product stats
    product_stats: Dict[int, dict] = {}
    weekday_vs_weekend: Dict[str, dict] = {
        "Weekdays": {"spend": 0.0, "count": 0},
        "Weekend": {"spend": 0.0, "count": 0},
    }
    time_of_day_buckets: Dict[str, dict] = {
        "Morning": {"spend": 0.0, "count": 0},
        "Afternoon": {"spend": 0.0, "count": 0},
        "Evening": {"spend": 0.0, "count": 0},
        "Late night": {"spend": 0.0, "count": 0},
    }

    # Habit aggregation: per habit label
    habit_totals: Dict[str, float] = defaultdict(float)
    habit_counts: Dict[str, int] = defaultdict(int)
    habit_weekday_spend: Dict[str, Dict[int, float]] = defaultdict(
        lambda: defaultdict(float)
    )

    for li, product, receipt in rows:
        if not receipt or not receipt.purchase_datetime:
            continue

        total_price = float(li.total_price or 0.0)
        ts = receipt.purchase_datetime

        # Product-level
        if product is not None:
            stats = product_stats.setdefault(
                product.id,
                {
                    "product": product,
                    "total_spend": 0.0,
                    "purchase_count": 0,
                    "last_purchase_at": None,
                },
            )
            stats["total_spend"] += total_price
            stats["purchase_count"] += 1
            if not stats["last_purchase_at"] or ts > stats["last_purchase_at"]:
                stats["last_purchase_at"] = ts

        # Weekday vs weekend
        weekday = ts.weekday()  # 0=Mon
        bucket = "Weekend" if weekday >= 5 else "Weekdays"
        weekday_vs_weekend[bucket]["spend"] += total_price
        weekday_vs_weekend[bucket]["count"] += 1

        # Time of day buckets
        hour = ts.hour
        if 5 <= hour < 12:
            tod = "Morning"
        elif 12 <= hour < 18:
            tod = "Afternoon"
        elif 18 <= hour < 23:
            tod = "Evening"
        else:
            tod = "Late night"
        time_of_day_buckets[tod]["spend"] += total_price
        time_of_day_buckets[tod]["count"] += 1

        # Habits derived from actual product categories
        if product and product.category:
            for habit in _HABITS:
                if product.category in habit.categories:
                    habit_totals[habit.label] += total_price
                    habit_counts[habit.label] += 1
                    habit_weekday_spend[habit.label][weekday] += total_price

    # Build ProductInsight objects sorted by spend
    product_insights: List[ProductInsight] = []
    for pid, stats in product_stats.items():
        product = stats["product"]
        product_insights.append(
            ProductInsight(
                product_id=product.id,
                normalized_name=product.normalized_name,
                category=product.category,
                total_spend=round(stats["total_spend"], 2),
                purchase_count=int(stats["purchase_count"]),
                last_purchase_at=stats["last_purchase_at"],
            )
        )

    product_insights.sort(key=lambda x: x.total_spend, reverse=True)

    # Top recurring products by purchase frequency
    top_recurring = sorted(
        product_insights,
        key=lambda x: x.purchase_count,
        reverse=True,
    )[:5]

    # Weekday vs weekend summary
    weekday_weekend_insights: List[TimeBucketInsight] = []
    for label in ("Weekdays", "Weekend"):
        data = weekday_vs_weekend[label]
        weekday_weekend_insights.append(
            TimeBucketInsight(
                label=label,
                total_spend=round(data["spend"], 2),
                purchase_count=int(data["count"]),
            )
        )

    # Time-of-day insights
    tod_insights: List[TimeBucketInsight] = []
    for label in ("Morning", "Afternoon", "Evening", "Late night"):
        data = time_of_day_buckets[label]
        tod_insights.append(
            TimeBucketInsight(
                label=label,
                total_spend=round(data["spend"], 2),
                purchase_count=int(data["count"]),
            )
        )

    # Habit insights: scale to monthly estimates based on period length
    scale = 30.0 / float(period_days) if period_days > 0 else 1.0
    habit_insights: List[HabitInsightOut] = []
    for habit in _HABITS:
        total = habit_totals.get(habit.label, 0.0)
        count = habit_counts.get(habit.label, 0)
        if count == 0:
            continue
        monthly_cost = round(total * scale, 2)
        freq_per_month = round(count * scale, 1)

        # Simple explanation copy
        explanation = (
            f"You bought {habit.label.lower()} {count} times in the last {period_days} days."
        )

        habit_insights.append(
            HabitInsightOut(
                label=habit.label,
                monthly_cost_estimate=monthly_cost,
                frequency_per_month=freq_per_month,
                explanation=explanation,
            )
        )

    habit_insights.sort(key=lambda h: h.monthly_cost_estimate, reverse=True)

    # Highlights for normal users
    highlights: List[InsightHighlight] = []

    if top_recurring:
        top = top_recurring[0]
        highlights.append(
            InsightHighlight(
                text=(
                    f"You bought {top.normalized_name.lower()} {top.purchase_count} "
                    f"times in the last {period_days} days."
                )
            )
        )

    if habit_insights:
        top_habit = habit_insights[0]
        highlights.append(
            InsightHighlight(
                text=(
                    f"{top_habit.label} was your highest recurring spend "
                    f"in the last {period_days} days."
                )
            )
        )

        # Snack weekday spike example
        snack = next((h for h in habit_insights if h.label == "Snacks"), None)
        if snack:
            w_spend = habit_weekday_spend.get("Snacks", {})
            if w_spend:
                # Find weekday with highest snack spend
                best_wd, best_val = max(w_spend.items(), key=lambda kv: kv[1])
                avg = sum(w_spend.values()) / max(len(w_spend), 1)
                if avg > 0 and best_val >= 1.5 * avg:
                    weekday_names = [
                        "Mondays",
                        "Tuesdays",
                        "Wednesdays",
                        "Thursdays",
                        "Fridays",
                        "Saturdays",
                        "Sundays",
                    ]
                    highlights.append(
                        InsightHighlight(
                            text=(
                                f"Your snack spending spikes on {weekday_names[best_wd]}."
                            )
                        )
                    )

    access = AccessSnapshot(
        tier="premium",
        enabled_features=[
            FEATURE_BASIC_STATISTICS,
            FEATURE_ADVANCED_HABIT_INSIGHTS,
            FEATURE_DEEPER_TRENDS,
        ],
        locked_features=[],
    )

    return InsightsSummary(
        period_days=period_days,
        generated_at=now,
        top_products=product_insights[:10],
        top_recurring_products=top_recurring,
        weekday_vs_weekend=weekday_weekend_insights,
        time_of_day=tod_insights,
        habits=habit_insights,
        highlights=highlights,
        access=access,
    )


def compute_insights_summary_for_access(
    db: Session,
    *,
    access: AccessContext,
    period_days: int = 30,
) -> InsightsSummary:
    summary = compute_insights_summary(db, period_days=period_days)

    enabled_features = [FEATURE_BASIC_STATISTICS]
    locked_features: list[str] = []
    upgrade_copy: str | None = None

    if access.allows(FEATURE_DEEPER_TRENDS):
        enabled_features.append(FEATURE_DEEPER_TRENDS)
    else:
        summary = summary.model_copy(
            update={
                "weekday_vs_weekend": [],
                "time_of_day": [],
            }
        )
        locked_features.append(FEATURE_DEEPER_TRENDS)

    if access.allows(FEATURE_ADVANCED_HABIT_INSIGHTS):
        enabled_features.append(FEATURE_ADVANCED_HABIT_INSIGHTS)
    else:
        summary = summary.model_copy(
            update={
                "habits": [],
                "highlights": [],
            }
        )
        locked_features.append(FEATURE_ADVANCED_HABIT_INSIGHTS)

    if locked_features:
        upgrade_copy = "Premium adds advanced habits and deeper trends without restricting scanning or product tracking."

    return summary.model_copy(
        update={
            "access": AccessSnapshot(
                tier=access.tier,
                enabled_features=enabled_features,
                locked_features=locked_features,
                upgrade_copy=upgrade_copy,
            )
        }
    )
