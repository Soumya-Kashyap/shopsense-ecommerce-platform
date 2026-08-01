from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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

    # 1. Decrement stock
    product.stock_qty -= 1

    # 2. Get or create default customer
    customer = db.query(models.Customer).first()
    if not customer:
        customer = models.Customer(name="ShopSense Direct Customer", email="checkout@example.com")
        db.add(customer)
        db.commit()
        db.refresh(customer)

    # 3. Create Transaction record
    transaction = models.Transaction(
        customer_id=customer.id,
        product_id=product.id,
        quantity=1,
        total_amount=round(product.price, 2),
        created_at=datetime.now(timezone.utc)
    )
    db.add(transaction)

    # 4. Record Activity Log with "Sale recorded:" terminology
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
