from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

router = APIRouter(
    tags=["Customers & Segmentation"]
)


@router.get(
    "/customers/segments",
    response_model=list[schemas.CustomerSegmentResponse],
    summary="Customer Spend Tier Segmentation",
    description="Groups customers by total transaction spend in ₹ INR and classifies them into value segments: 'High Value' (>= ₹1,00,000), 'Medium Value' (₹25,000 - ₹99,999), or 'Low Value' (< ₹25,000).",
    response_description="List of customers with spend stats and tier segment classifications"
)
def get_customer_segments(db: Session = Depends(get_db)):
    customers = db.query(models.Customer).all()
    results = []

    for c in customers:
        stats = (
            db.query(
                func.sum(models.Transaction.total_amount).label("total_spend"),
                func.count(models.Transaction.id).label("total_orders")
            )
            .filter(models.Transaction.customer_id == c.id)
            .first()
        )

        spend = float(stats.total_spend) if stats and stats.total_spend else 0.0
        orders = int(stats.total_orders) if stats and stats.total_orders else 0

        if spend >= 100000.0:
            segment_label = "High Value"
        elif spend >= 25000.0:
            segment_label = "Medium Value"
        else:
            segment_label = "Low Value"

        results.append({
            "customer_id": c.id,
            "customer_name": c.name,
            "email": c.email,
            "total_spend": round(spend, 2),
            "total_orders": orders,
            "segment": segment_label
        })

    results.sort(key=lambda x: x["total_spend"], reverse=True)
    return results
