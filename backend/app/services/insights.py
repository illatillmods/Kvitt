from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import List

from app.services.normalization import NormalizedReceipt


@dataclass
class HabitInsight:
    label: str
    monthly_cost_estimate: float
    frequency_per_month: float


def simple_habit_insights(receipts: List[NormalizedReceipt]) -> List[HabitInsight]:
    """Very small, non-persistent insight engine.

    In MVP we will likely call this per-user over the last N receipts.
    Here we only sketch the API and a trivial implementation so the
    rest of the system can evolve without being blocked.
    """

    # Flatten all items
    items = [li for r in receipts for li in r.line_items]
    now = datetime.utcnow()

    # Group by category for now
    by_category: dict[str, list[float]] = {}
    for li in items:
        if not li.category:
            continue
        by_category.setdefault(li.category, []).append(li.total_price)

    insights: List[HabitInsight] = []
    for category, amounts in by_category.items():
        total = float(sum(amounts))
        # Naive: assume data roughly covers one month
        insights.append(
            HabitInsight(
                label=category,
                monthly_cost_estimate=round(total, 2),
                frequency_per_month=len(amounts),
            )
        )

    # Sort by spend desc
    insights.sort(key=lambda x: x.monthly_cost_estimate, reverse=True)
    return insights
