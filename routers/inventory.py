from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas

router = APIRouter(
    tags=["Inventory"]
)


@router.get("/inventory/overview", response_model=list[schemas.InventoryItemResponse])
def get_inventory_overview(db: Session = Depends(get_db)):
    """
    Inventory Intelligence Endpoint (Milestone 2):
    Returns product name, vendor name, stock quantity, price, and computed status ("low_stock" vs "in_stock")
    for every product across all vendors.
    """
    products = db.query(models.Product).join(models.Vendor, models.Product.vendor_id == models.Vendor.id).all()
    results = []

    for p in products:
        status_val = "low_stock" if p.stock_qty < 10 else "in_stock"
        results.append({
            "product_id": p.id,
            "product_name": p.name,
            "vendor_id": p.vendor_id,
            "vendor_name": p.vendor.name if p.vendor else "Unknown Vendor",
            "stock_qty": p.stock_qty,
            "price": p.price,
            "status": status_val
        })

    return results


@router.get("/inventory/low-stock", response_model=list[schemas.InventoryItemResponse])
def get_low_stock_inventory(db: Session = Depends(get_db)):
    """
    Inventory Low Stock Endpoint (Milestone 2):
    Returns only products currently below the low-stock threshold (stock_qty < 10) across all vendors
    for admin-wide visibility.
    """
    products = (
        db.query(models.Product)
        .join(models.Vendor, models.Product.vendor_id == models.Vendor.id)
        .filter(models.Product.stock_qty < 10)
        .all()
    )
    results = []

    for p in products:
        results.append({
            "product_id": p.id,
            "product_name": p.name,
            "vendor_id": p.vendor_id,
            "vendor_name": p.vendor.name if p.vendor else "Unknown Vendor",
            "stock_qty": p.stock_qty,
            "price": p.price,
            "status": "low_stock"
        })

    return results
