from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
import models
import schemas

router = APIRouter(
    tags=["Customers"]
)


@router.get("/customers/segments", response_model=list[schemas.CustomerSegmentResponse])
def get_customer_segments(db: Session = Depends(get_db)):
    """
    Customer Segmentation Endpoint (Milestone 2):
    Groups customers by total transaction spend and classifies them into:
    - "High Value" (>= ₹1,00,000)
    - "Medium Value" (₹25,000 - ₹99,999)
    - "Low Value" (< ₹25,000)
    """
    customers = db.query(models.Customer).all()
    results = []

    for c in customers:
        # Sum total_amount and count orders for this customer
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

        # Classification logic
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

    # Sort customers by total spend descending
    results.sort(key=lambda x: x["total_spend"], reverse=True)
    return results
