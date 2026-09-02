from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database import get_db
import models
import schemas

router = APIRouter(
    prefix="/charts",
    tags=["Chart-Ready Analytics (Milestone 3)"]
)


@router.get("/revenue-by-vendor", response_model=list[schemas.ChartItemResponse])
def get_chart_revenue_by_vendor(db: Session = Depends(get_db)):
    """
    1. GET /charts/revenue-by-vendor:
    Returns each vendor's name and total revenue, sorted descending.
    Format: [{"label": "Samsung", "value": 388996.00}, ...]
    """
    query = (
        db.query(
            models.Vendor.name.label("vendor_name"),
            func.coalesce(func.sum(models.Transaction.total_amount), 0.0).label("total_revenue")
        )
        .filter(models.Vendor.role == "vendor")
        .outerjoin(models.Product, models.Vendor.id == models.Product.vendor_id)
        .outerjoin(models.Transaction, models.Product.id == models.Transaction.product_id)
        .group_by(models.Vendor.id, models.Vendor.name)
        .order_by(desc("total_revenue"))
        .all()
    )

    results = []
    for r in query:
        results.append({
            "label": r.vendor_name,
            "value": round(float(r.total_revenue), 2)
        })

    return results


@router.get("/daily-orders-trend", response_model=list[schemas.ChartItemResponse])
def get_chart_daily_orders_trend(db: Session = Depends(get_db)):
    """
    2. GET /charts/daily-orders-trend:
    Returns order count per day for the last 7 days.
    Format: [{"label": "Mon 08-18", "value": 5}, ...]
    """
    now_utc = datetime.now(timezone.utc)
    days_list = [now_utc - timedelta(days=i) for i in range(6, -1, -1)]

    results = []
    for d in days_list:
        date_str = d.strftime("%Y-%m-%d")
        lbl = d.strftime("%a %m-%d")  # e.g. "Mon 08-18"

        stats = (
            db.query(func.coalesce(func.count(models.Transaction.id), 0).label("orders"))
            .filter(func.date(models.Transaction.created_at) == date_str)
            .first()
        )

        ord_cnt = int(stats.orders) if stats and stats.orders else 0
        results.append({
            "label": lbl,
            "value": float(ord_cnt)
        })

    return results


@router.get("/customer-segment-distribution", response_model=list[schemas.ChartItemResponse])
def get_chart_customer_segment_distribution(db: Session = Depends(get_db)):
    """
    3. GET /charts/customer-segment-distribution:
    Returns count of customers in each segment (High/Medium/Low Value) with badge colors.
    Format: [
      {"label": "High Value", "value": 3, "color": "#facc15"},
      {"label": "Medium Value", "value": 2, "color": "#60a5fa"},
      {"label": "Low Value", "value": 1, "color": "#94a3b8"}
    ]
    """
    customers = db.query(models.Customer).all()

    high_count = 0
    med_count = 0
    low_count = 0

    for c in customers:
        total_spend = (
            db.query(func.coalesce(func.sum(models.Transaction.total_amount), 0.0))
            .filter(models.Transaction.customer_id == c.id)
            .scalar()
        ) or 0.0

        if total_spend >= 100000.0:
            high_count += 1
        elif total_spend >= 25000.0:
            med_count += 1
        else:
            low_count += 1

    return [
        {"label": "High Value", "value": float(high_count), "color": "#facc15"},
        {"label": "Medium Value", "value": float(med_count), "color": "#60a5fa"},
        {"label": "Low Value", "value": float(low_count), "color": "#94a3b8"}
    ]


@router.get("/category-sales-breakdown", response_model=list[schemas.ChartItemResponse])
def get_chart_category_sales_breakdown(db: Session = Depends(get_db)):
    """
    4. GET /charts/category-sales-breakdown:
    Returns total revenue per product category (based on VISION category field).
    Format: [{"label": "Electronics", "value": 150000.00}, ...]
    """
    query = (
        db.query(
            models.Product.category.label("raw_cat"),
            func.coalesce(func.sum(models.Transaction.total_amount), 0.0).label("revenue")
        )
        .outerjoin(models.Transaction, models.Product.id == models.Transaction.product_id)
        .group_by(models.Product.category)
        .order_by(desc("revenue"))
        .all()
    )

    # Group by clean category name
    cat_map = {}
    for r in query:
        raw_cat = r.raw_cat or "Electronics"
        clean_cat = raw_cat.replace("VISION: ", "").strip()
        rev = float(r.revenue)
        cat_map[clean_cat] = cat_map.get(clean_cat, 0.0) + rev

    results = []
    for cat_name, rev_val in cat_map.items():
        results.append({
            "label": cat_name,
            "value": round(rev_val, 2)
        })

    # Sort descending by value
    results.sort(key=lambda x: x["value"], reverse=True)
    return results
