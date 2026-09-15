from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

router = APIRouter(
    tags=["Analytics & Benchmarking"]
)


@router.get(
    "/analytics/sales-trend",
    response_model=list[schemas.SalesTrendDayItem],
    summary="7-Day Daily Platform Sales Trend",
    description="Returns total daily revenue (₹ INR) and order volume grouped by day for the past 7 consecutive days.",
    response_description="Chronological list of 7 daily sales trend data points"
)
def get_sales_trend_analytics(db: Session = Depends(get_db)):
    now_utc = datetime.now(timezone.utc)
    days_list = [now_utc - timedelta(days=i) for i in range(6, -1, -1)]

    results = []

    for d in days_list:
        date_str = d.strftime("%Y-%m-%d")
        day_name = d.strftime("%a")

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


@router.get(
    "/analytics/benchmarks",
    response_model=schemas.VendorBenchmarkResponse,
    summary="Vendor Performance Marketplace Benchmarking",
    description="Calculates platform-wide marketplace baselines (Average Revenue per Vendor, Average Order Value, Average Units per Vendor) and classifies each merchant as 'Above Average', 'Average', or 'Below Average'.",
    response_description="Marketplace average baselines and per-vendor performance benchmark metrics"
)
def get_vendor_benchmarks(db: Session = Depends(get_db)):
    vendors = db.query(models.Vendor).filter(models.Vendor.role == "vendor").all()
    vendor_count = len(vendors)

    total_revenue_platform = (
        db.query(func.coalesce(func.sum(models.Transaction.total_amount), 0.0)).scalar()
    ) or 0.0

    total_orders_platform = (
        db.query(func.coalesce(func.count(models.Transaction.id), 0)).scalar()
    ) or 0

    total_units_platform = (
        db.query(func.coalesce(func.sum(models.Transaction.quantity), 0)).scalar()
    ) or 0

    avg_revenue_per_vendor = round(total_revenue_platform / max(vendor_count, 1), 2)
    avg_order_value = round(total_revenue_platform / max(total_orders_platform, 1), 2)
    avg_units_per_vendor = round(total_units_platform / max(vendor_count, 1), 1)

    vendor_benchmark_items = []

    for v in vendors:
        v_stats = (
            db.query(
                func.coalesce(func.sum(models.Transaction.total_amount), 0.0).label("revenue"),
                func.coalesce(func.count(models.Transaction.id), 0).label("orders"),
                func.coalesce(func.sum(models.Transaction.quantity), 0).label("units_sold")
            )
            .join(models.Product, models.Transaction.product_id == models.Product.id)
            .filter(models.Product.vendor_id == v.id)
            .first()
        )

        v_rev = round(float(v_stats.revenue), 2) if v_stats and v_stats.revenue else 0.0
        v_orders = int(v_stats.orders) if v_stats and v_stats.orders else 0
        v_units = int(v_stats.units_sold) if v_stats and v_stats.units_sold else 0
        v_aov = round(v_rev / max(v_orders, 1), 2) if v_orders > 0 else 0.0

        if avg_revenue_per_vendor > 0:
            if v_rev >= (1.15 * avg_revenue_per_vendor):
                perf = "Above Average"
            elif v_rev <= (0.85 * avg_revenue_per_vendor):
                perf = "Below Average"
            else:
                perf = "Average"
        else:
            perf = "Above Average" if v_rev > 0 else "Average"

        vendor_benchmark_items.append({
            "vendor_id": v.id,
            "vendor_name": v.name,
            "email": v.email,
            "revenue": v_rev,
            "orders": v_orders,
            "aov": v_aov,
            "units_sold": v_units,
            "performance": perf
        })

    vendor_benchmark_items.sort(key=lambda x: x["revenue"], reverse=True)

    return {
        "marketplace_averages": {
            "avg_revenue_per_vendor": avg_revenue_per_vendor,
            "avg_order_value": avg_order_value,
            "avg_units_per_vendor": avg_units_per_vendor
        },
        "vendors": vendor_benchmark_items
    }
