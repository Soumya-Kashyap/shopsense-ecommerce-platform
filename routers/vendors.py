from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas
from auth import hash_password, verify_password
from database import get_db

router = APIRouter(
    tags=["Vendors & Merchants"]
)


@router.post(
    "/login",
    response_model=schemas.LoginResponse,
    summary="Authenticate User or Vendor",
    description="Authenticates System Administrator or Vendor credentials via bcrypt verification and returns authorization session token.",
    response_description="User identity, role, vendor ID, and authorization session token"
)
def login(credentials: schemas.LoginRequest, db: Session = Depends(get_db)):
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


@router.post(
    "/vendors/register",
    response_model=schemas.VendorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New Merchant Vendor",
    description="Registers a new merchant vendor account with status initialized to 'pending' for administrative approval.",
    response_description="Newly created vendor record object"
)
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


@router.get(
    "/vendors/",
    response_model=list[schemas.VendorResponse],
    summary="List All Vendors",
    description="Retrieves a complete list of all registered merchant vendors.",
    response_description="List of vendor record objects"
)
def list_vendors(db: Session = Depends(get_db)):
    return db.query(models.Vendor).all()


@router.get(
    "/vendors/revenue-summary",
    summary="Per-Vendor Revenue & Order Breakdown",
    description="Calculates gross revenue (₹ INR), order counts, and total units sold for every registered vendor merchant.",
    response_description="List of per-vendor sales summary statistics"
)
def get_per_vendor_revenue(db: Session = Depends(get_db)):
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


@router.get(
    "/vendors/{vendor_id}",
    response_model=schemas.VendorResponse,
    summary="Get Vendor Details by ID",
    description="Retrieves profile and account status information for a specific vendor ID.",
    response_description="Vendor profile record object"
)
def get_vendor(vendor_id: int, db: Session = Depends(get_db)):
    vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {vendor_id} not found."
        )
    return vendor


@router.put(
    "/vendors/{vendor_id}",
    response_model=schemas.VendorResponse,
    summary="Update Vendor Profile Details",
    description="Updates name, email, or contact information for an existing vendor.",
    response_description="Updated vendor record object"
)
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


@router.put(
    "/vendors/{vendor_id}/status",
    response_model=schemas.VendorResponse,
    summary="Update Vendor Account Approval Status",
    description="Admin control endpoint to set vendor status to 'active', 'pending', or 'suspended'. Logs activity stream event.",
    response_description="Vendor object with updated status"
)
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


@router.get(
    "/vendors/{vendor_id}/sales",
    response_model=schemas.VendorSalesSummary,
    summary="Get Specific Vendor Sales Metrics",
    description="Returns aggregate sales performance metrics (total orders, total units sold, total revenue) for a single vendor.",
    response_description="Vendor sales summary metrics object"
)
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
