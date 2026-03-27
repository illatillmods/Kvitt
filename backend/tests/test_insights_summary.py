from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.merchant import Merchant
from app.models.product import Product
from app.models.receipt import Receipt
from app.models.line_item import LineItem
from app.services.insights import compute_insights_summary
from tests.utils_db import test_db_session


def _seed_basic_history(db: Session) -> None:
    merchant = Merchant(name="Test Store", country_code="SE")
    db.add(merchant)

    beer = Product(normalized_name="Starköl", category="beer")
    snacks = Product(normalized_name="Chips", category="snacks")
    energy = Product(normalized_name="Red Bull", category="energy_drink")
    db.add_all([beer, snacks, energy])
    db.flush()

    now = datetime.utcnow()

    # Create a few receipts over the last 10 days
    for i in range(10):
        dt = now - timedelta(days=i)
        r = Receipt(
            merchant=merchant,
            purchase_datetime=dt,
            total_amount=100,
            currency="SEK",
            raw_text=None,
        )
        db.add(r)
        db.flush([r])

        # Alternate between products
        if i % 3 == 0:
            p = beer
        elif i % 3 == 1:
            p = snacks
        else:
            p = energy

        li = LineItem(
            receipt_id=r.id,
            product_id=p.id,
            raw_description=p.normalized_name,
            quantity=1,
            unit_price=50,
            total_price=50,
        )
        db.add(li)

    db.commit()


def test_compute_insights_summary_basic():
    with test_db_session() as db:
        _seed_basic_history(db)
        summary = compute_insights_summary(db, period_days=30)

    assert summary.period_days == 30
    assert summary.top_products
    assert summary.top_recurring_products
    assert summary.weekday_vs_weekend
    assert summary.time_of_day
    assert summary.habits
    assert summary.highlights
