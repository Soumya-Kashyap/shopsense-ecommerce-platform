from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database import get_db
import models
import schemas

router = APIRouter(
    tags=["Products"]
)


@router.post("/products", response_model=schemas.ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    """
    Create a new product linked to a specific vendor, including AI category and tags.
    """
    vendor = db.query(models.Vendor).filter(models.Vendor.id == product.vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {product.vendor_id} not found."
        )

    db_product = models.Product(
        vendor_id=product.vendor_id,
        name=product.name,
        price=product.price,
        description=product.description,
        image_url=product.image_url,
        category=product.category,
        tags=product.tags,
        stock_qty=product.stock_qty
    )
    db.add(db_product)

    log_entry = models.ActivityLog(
        event_type="product_added",
        description=f"Vendor '{vendor.name}' added new product '{product.name}' (₹{product.price:,.2f}).",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)

    db.commit()
    db.refresh(db_product)
    return db_product


@router.get("/products/top-selling", response_model=list[schemas.TopSellingProductResponse])
def get_top_selling_products(
    category: Optional[str] = None,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """
    Rule-Based Product Recommendations Endpoint (Milestone 2):
    Returns top-selling products ranked by total units sold across completed transactions.
    Supports optional category filtering.
    """
    query = (
        db.query(
            models.Product.id.label("product_id"),
            models.Product.name.label("product_name"),
            models.Product.vendor_id.label("vendor_id"),
            models.Vendor.name.label("vendor_name"),
            models.Product.category.label("category"),
            models.Product.price.label("price"),
            func.coalesce(func.sum(models.Transaction.quantity), 0).label("units_sold"),
            func.coalesce(func.sum(models.Transaction.total_amount), 0.0).label("total_revenue")
        )
        .join(models.Vendor, models.Product.vendor_id == models.Vendor.id)
        .outerjoin(models.Transaction, models.Product.id == models.Transaction.product_id)
    )

    if category and category.strip() and category.strip().lower() != "all categories":
        search_cat = category.strip()
        query = query.filter(models.Product.category.ilike(f"%{search_cat}%"))

    top_products = (
        query.group_by(
            models.Product.id,
            models.Product.name,
            models.Product.vendor_id,
            models.Vendor.name,
            models.Product.category,
            models.Product.price
        )
        .order_by(desc("units_sold"), desc("total_revenue"))
        .limit(limit)
        .all()
    )

    results = []
    for p in top_products:
        results.append({
            "product_id": p.product_id,
            "product_name": p.product_name,
            "vendor_id": p.vendor_id,
            "vendor_name": p.vendor_name,
            "category": p.category or "VISION: Electronics",
            "price": float(p.price),
            "units_sold": int(p.units_sold),
            "total_revenue": round(float(p.total_revenue), 2)
        })

    return results


@router.post("/products/{product_id}/simulate-sale")
def simulate_product_sale(product_id: int, db: Session = Depends(get_db)):
    """
    FEATURE: Records a transaction for 1 unit of this product.
    - Decrements stock_qty by 1.
    - Creates a Transaction record.
    - Logs a live ActivityLog event.
    """
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found."
        )

    if product.stock_qty <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product '{product.name}' is out of stock!"
        )

    product.stock_qty -= 1

    customer = db.query(models.Customer).first()
    if not customer:
        customer = models.Customer(name="ShopSense Direct Customer", email="checkout@example.com")
        db.add(customer)
        db.commit()
        db.refresh(customer)

    transaction = models.Transaction(
        customer_id=customer.id,
        product_id=product.id,
        quantity=1,
        total_amount=round(product.price, 2),
        created_at=datetime.now(timezone.utc)
    )
    db.add(transaction)

    vendor_name = product.vendor.name if product.vendor else "Vendor"
    log_entry = models.ActivityLog(
        event_type="sale_simulated",
        description=f"Sale recorded: {vendor_name} sold 1x '{product.name}' for ₹{product.price:,.2f}.",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)

    db.commit()
    db.refresh(product)

    return {
        "message": f"Successfully recorded sale of '{product.name}'!",
        "product_id": product.id,
        "remaining_stock": product.stock_qty,
        "sale_amount": round(product.price, 2),
        "transaction_id": transaction.id
    }


@router.post("/products/{product_id}/restock", response_model=schemas.RestockResponse)
def restock_product_inventory(
    product_id: int,
    restock: schemas.RestockRequest,
    db: Session = Depends(get_db)
):
    """
    RESTOCK INVENTORY FEATURE (Milestone 2):
    Adds specified quantity to product's stock_qty and logs an ActivityLog entry.
    """
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found."
        )

    product.stock_qty += restock.quantity
    vendor_name = product.vendor.name if product.vendor else "Vendor"

    log_entry = models.ActivityLog(
        event_type="product_restocked",
        description=f"{vendor_name} restocked '{product.name}' by {restock.quantity} units - new stock: {product.stock_qty}.",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)

    db.commit()
    db.refresh(product)

    return {
        "product_id": product.id,
        "product_name": product.name,
        "quantity_added": restock.quantity,
        "new_stock_qty": product.stock_qty,
        "message": f"Successfully restocked '{product.name}' by {restock.quantity} units! New stock: {product.stock_qty}."
    }


@router.get("/vendors/{vendor_id}/products", response_model=list[schemas.ProductResponse])
def get_vendor_products(vendor_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all products listed by a specific vendor.
    """
    vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {vendor_id} not found."
        )

    return db.query(models.Product).filter(models.Product.vendor_id == vendor_id).all()
