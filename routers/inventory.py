from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

router = APIRouter(
    tags=["Inventory & Stock Intelligence"]
)


@router.get(
    "/inventory/overview",
    response_model=list[schemas.InventoryItemResponse],
    summary="Platform Inventory Overview",
    description="Retrieves stock quantity, unit price (₹ INR), vendor identity, and calculated inventory status badge ('low_stock' if stock_qty < 10, else 'in_stock') for all marketplace products.",
    response_description="List of inventory items with calculated stock status"
)
def get_inventory_overview(db: Session = Depends(get_db)):
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


@router.get(
    "/inventory/low-stock",
    response_model=list[schemas.InventoryItemResponse],
    summary="Low Stock Inventory Alerts",
    description="Filters marketplace catalog for items below critical restock threshold (stock_qty < 10 units) across all vendors.",
    response_description="List of low-stock inventory items"
)
def get_low_stock_inventory(db: Session = Depends(get_db)):
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
