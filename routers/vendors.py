from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
import models
import schemas
from auth import hash_password, verify_password

router = APIRouter(
    tags=["Vendors"]
)


@router.post("/login", response_model=schemas.LoginResponse)
def login(credentials: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate vendor or admin users using bcrypt verification.
    """
    user = db.query(models.Vendor).filter(models.Vendor.email == credentials.email).first()
    if not user or not user.password_hash or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password."
        )

    if user.status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your vendor account has been rejected or suspended. Please contact platform administration."
        )

    token = f"session_token_{user.id}_{user.role}"
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "status": user.status,
        "vendor_id": user.id,
        "name": user.name,
        "email": user.email
    }


@router.post("/vendors/register", response_model=schemas.VendorResponse, status_code=status.HTTP_201_CREATED)
def register_vendor(vendor: schemas.VendorCreate, db: Session = Depends(get_db)):
    existing_vendor = db.query(models.Vendor).filter(models.Vendor.email == vendor.email).first()
    if existing_vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A vendor with this email address already exists."
        )

    db_vendor = models.Vendor(
        name=vendor.name,
        email=vendor.email,
        password_hash=hash_password(vendor.password),
        role="vendor",
        status="pending",
        phone=vendor.phone
    )
    db.add(db_vendor)
    
    log_entry = models.ActivityLog(
        event_type="vendor_registered",
        description=f"New vendor '{vendor.name}' registered (Status: PENDING)."
    )
    db.add(log_entry)
    
    db.commit()
    db.refresh(db_vendor)
    return db_vendor


@router.get("/vendors/", response_model=list[schemas.VendorResponse])
def list_vendors(db: Session = Depends(get_db)):
    return db.query(models.Vendor).all()


@router.get("/vendors/revenue-summary")
def get_per_vendor_revenue(db: Session = Depends(get_db)):
    """
    Analytics Endpoint: Returns per-vendor financial breakdown (orders, units, revenue in ₹ INR).
    """
    vendors = db.query(models.Vendor).filter(models.Vendor.role == "vendor").all()
    summary = []

    for v in vendors:
        stats = (
            db.query(
                func.count(models.Transaction.id).label("total_orders"),
                func.sum(models.Transaction.quantity).label("units_sold"),
                func.sum(models.Transaction.total_amount).label("total_revenue")
            )
            .join(models.Product, models.Transaction.product_id == models.Product.id)
            .filter(models.Product.vendor_id == v.id)
            .first()
        )

        orders = int(stats.total_orders) if stats and stats.total_orders else 0
        units = int(stats.units_sold) if stats and stats.units_sold else 0
        revenue = float(stats.total_revenue) if stats and stats.total_revenue else 0.0

        summary.append({
            "vendor_id": v.id,
            "vendor_name": v.name,
            "email": v.email,
            "status": v.status,
            "total_orders": orders,
            "total_units_sold": units,
            "total_revenue": round(revenue, 2)
        })

    return summary


@router.get("/vendors/{vendor_id}", response_model=schemas.VendorResponse)
def get_vendor(vendor_id: int, db: Session = Depends(get_db)):
    vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {vendor_id} not found."
        )
    return vendor


@router.put("/vendors/{vendor_id}", response_model=schemas.VendorResponse)
def update_vendor(vendor_id: int, vendor_data: schemas.VendorUpdate, db: Session = Depends(get_db)):
    vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {vendor_id} not found."
        )

    if vendor_data.email and vendor_data.email != vendor.email:
        email_check = db.query(models.Vendor).filter(models.Vendor.email == vendor_data.email).first()
        if email_check:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already in use by another vendor."
            )

    update_dict = vendor_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(vendor, key, value)

    db.commit()
    db.refresh(vendor)
    return vendor


@router.put("/vendors/{vendor_id}/status", response_model=schemas.VendorResponse)
def update_vendor_status(vendor_id: int, status_data: schemas.VendorStatusUpdate, db: Session = Depends(get_db)):
    vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {vendor_id} not found."
        )

    old_status = vendor.status
    vendor.status = status_data.status

    display_status = "REJECTED" if status_data.status == "suspended" else status_data.status.upper()
    log_entry = models.ActivityLog(
        event_type="status_changed",
        description=f"Vendor '{vendor.name}' status updated from {old_status.upper()} to {display_status}."
    )
    db.add(log_entry)

    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/vendors/{vendor_id}/sales", response_model=schemas.VendorSalesSummary)
def get_vendor_sales_summary(vendor_id: int, db: Session = Depends(get_db)):
    vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {vendor_id} not found."
        )

    stats = (
        db.query(
            func.count(models.Transaction.id).label("total_orders"),
            func.sum(models.Transaction.quantity).label("units_sold"),
            func.sum(models.Transaction.total_amount).label("total_revenue")
        )
        .join(models.Product, models.Transaction.product_id == models.Product.id)
        .filter(models.Product.vendor_id == vendor_id)
        .first()
    )

    orders = int(stats.total_orders) if stats and stats.total_orders else 0
    units = int(stats.units_sold) if stats and stats.units_sold else 0
    revenue = float(stats.total_revenue) if stats and stats.total_revenue else 0.0

    return {
        "vendor_id": vendor.id,
        "vendor_name": vendor.name,
        "total_orders": orders,
        "total_units_sold": units,
        "total_revenue": round(revenue, 2)
    }
