from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

router = APIRouter(
    prefix="/charts",
    tags=["Visual Charts & Graph Data"]
)


@router.get(
    "/revenue-by-vendor",
    response_model=list[schemas.ChartItemResponse],
    summary="Chart Data: Revenue by Vendor",
    description="Returns each merchant vendor's total revenue formatted as pre-processed {label, value} objects sorted descending for bar chart rendering.",
    response_description="Array of chart item objects for vendor revenue bar chart"
)
def get_chart_revenue_by_vendor(db: Session = Depends(get_db)):
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


@router.get(
    "/daily-orders-trend",
    response_model=list[schemas.ChartItemResponse],
    summary="Chart Data: 7-Day Order Volume Trend",
    description="Returns order counts per day for the last 7 days formatted as {label, value} objects for trendline chart rendering.",
    response_description="Array of chart item objects for daily order trend graph"
)
def get_chart_daily_orders_trend(db: Session = Depends(get_db)):
    now_utc = datetime.now(timezone.utc)
    days_list = [now_utc - timedelta(days=i) for i in range(6, -1, -1)]

    results = []
    for d in days_list:
        date_str = d.strftime("%Y-%m-%d")
        lbl = d.strftime("%a %m-%d")

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


@router.get(
    "/customer-segment-distribution",
    response_model=list[schemas.ChartItemResponse],
    summary="Chart Data: Customer Segment Share",
    description="Returns customer counts per spend tier (High, Medium, Low Value) formatted with UI hex color codes for donut/pie chart rendering.",
    response_description="Array of chart item objects with associated hex color strings"
)
def get_chart_customer_segment_distribution(db: Session = Depends(get_db)):
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


@router.get(
    "/category-sales-breakdown",
    response_model=list[schemas.ChartItemResponse],
    summary="Chart Data: Revenue by Product Category",
    description="Returns total sales revenue grouped by product category classification formatted as {label, value} objects sorted descending.",
    response_description="Array of chart item objects for category revenue breakdown chart"
)
def get_chart_category_sales_breakdown(db: Session = Depends(get_db)):
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

    results.sort(key=lambda x: x["value"], reverse=True)
    return results
