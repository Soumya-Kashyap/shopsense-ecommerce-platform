from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
import models
import schemas

router = APIRouter(
    tags=["Analytics"]
)


@router.get("/analytics/sales-trend", response_model=list[schemas.SalesTrendDayItem])
def get_sales_trend_analytics(db: Session = Depends(get_db)):
    """
    SALES TREND CHART FEATURE (Milestone 2):
    Returns daily total revenue and orders grouped by day for the last 7 days.
    """
    now_utc = datetime.now(timezone.utc)
    # Generate list of dates from 6 days ago up to today (7 days total)
    days_list = [now_utc - timedelta(days=i) for i in range(6, -1, -1)]

    results = []

    for d in days_list:
        date_str = d.strftime("%Y-%m-%d")
        day_name = d.strftime("%a")  # "Mon", "Tue", etc.

        # Query transactions created on this specific calendar date
        stats = (
            db.query(
                func.coalesce(func.sum(models.Transaction.total_amount), 0.0).label("revenue"),
                func.coalesce(func.count(models.Transaction.id), 0).label("orders")
            )
            .filter(func.date(models.Transaction.created_at) == date_str)
            .first()
        )

        rev = float(stats.revenue) if stats and stats.revenue else 0.0
        ord_cnt = int(stats.orders) if stats and stats.orders else 0

        results.append({
            "date": date_str,
            "day_label": day_name,
            "revenue": round(rev, 2),
            "orders": ord_cnt
        })

    return results
