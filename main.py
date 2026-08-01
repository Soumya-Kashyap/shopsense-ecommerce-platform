import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

import models
import schemas
from database import engine, get_db, SessionLocal
from routers import vendors, products
from auth import hash_password

# Create database tables automatically on startup if they do not exist
models.Base.metadata.create_all(bind=engine)


def init_admin_user():
    """
    Ensures the special administrator account exists on application launch.
    Email: admin@shopsense.com | Password: admin | Role: admin | Status: active
    """
    db = SessionLocal()
    try:
        admin = db.query(models.Vendor).filter(models.Vendor.email == "admin@shopsense.com").first()
        if not admin:
            admin = models.Vendor(
                name="ShopSense Administrator",
                email="admin@shopsense.com",
                password_hash=hash_password("admin"),
                role="admin",
                status="active",
                phone="+1-800-ADMIN-01"
            )
            db.add(admin)
            db.commit()
            print("🔑 System Administrator account initialized (admin@shopsense.com / admin)")
    finally:
        db.close()


# Run admin initialization
init_admin_user()

# Initialize FastAPI application
app = FastAPI(
    title="ShopSense API",
    description="Multi-Vendor E-Commerce Analytics Platform with Auth & Activity Feed",
    version="1.3.1"
)

# Enable CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints from routers
app.include_router(vendors.router)
app.include_router(products.router)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to ShopSense API: Multi-Vendor E-Commerce Analytics Platform",
        "docs_url": "http://127.0.0.1:8000/docs",
        "login_url": "http://127.0.0.1:8000/login-page",
        "admin_dashboard_url": "http://127.0.0.1:8000/admin-dashboard",
        "vendor_dashboard_url": "http://127.0.0.1:8000/vendor-dashboard",
        "currency": "INR (₹)",
        "milestone": "Milestone 1 - Auth, RBAC, Vendor Analytics, Activity Feed & Catalog"
    }


@app.get("/stats")
def get_global_stats(db: Session = Depends(get_db)):
    """
    Analytics Endpoint: Global platform metrics, revenue in ₹ INR, and Top Vendor of the Month.
    """
    active_vendors = db.query(models.Vendor).filter(models.Vendor.role == "vendor", models.Vendor.status == "active").count()
    catalog_products = db.query(models.Product).count()
    total_transactions = db.query(models.Transaction).count()

    # Calculate Total Platform Revenue joining active products & vendors
    total_revenue_result = (
        db.query(func.sum(models.Transaction.total_amount))
        .join(models.Product, models.Transaction.product_id == models.Product.id)
        .join(models.Vendor, models.Product.vendor_id == models.Vendor.id)
        .filter(models.Vendor.role == "vendor")
        .scalar()
    )
    total_revenue = float(total_revenue_result) if total_revenue_result else 0.0

    # Calculate Top Vendor of the Month (Vendor with highest total revenue in Transactions)
    top_vendor_query = (
        db.query(
            models.Vendor.name.label("vendor_name"),
            func.sum(models.Transaction.total_amount).label("total_rev"),
            func.count(models.Transaction.id).label("orders_count")
        )
        .join(models.Product, models.Vendor.id == models.Product.vendor_id)
        .join(models.Transaction, models.Product.id == models.Transaction.product_id)
        .filter(models.Vendor.role == "vendor")
        .group_by(models.Vendor.id, models.Vendor.name)
        .order_by(desc(func.sum(models.Transaction.total_amount)))
        .first()
    )

    if top_vendor_query and top_vendor_query.total_rev is not None:
        top_vendor_data = {
            "name": top_vendor_query.vendor_name,
            "revenue": round(float(top_vendor_query.total_rev), 2),
            "orders": int(top_vendor_query.orders_count)
        }
    else:
        # Fallback to first active vendor if no transactions yet
        first_vendor = db.query(models.Vendor).filter(models.Vendor.role == "vendor", models.Vendor.status == "active").first()
        top_vendor_data = {
            "name": first_vendor.name if first_vendor else "Samsung",
            "revenue": 0.0,
            "orders": 0
        }

    return {
        "total_revenue": round(total_revenue, 2),
        "active_vendors": active_vendors,
        "catalog_products": catalog_products,
        "total_transactions": total_transactions,
        "top_vendor": top_vendor_data
    }


@app.get("/activity-feed", response_model=list[schemas.ActivityLogResponse])
def get_activity_feed(db: Session = Depends(get_db)):
    """
    Returns the 10 most recent system activity events.
    """
    return db.query(models.ActivityLog).order_by(desc(models.ActivityLog.timestamp)).limit(10).all()


@app.get("/login-page")
def serve_login_page():
    path = os.path.join(os.path.dirname(__file__), "login.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "login.html file not found"}


@app.get("/admin-dashboard")
def serve_admin_dashboard():
    path = os.path.join(os.path.dirname(__file__), "admin_dashboard.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "admin_dashboard.html file not found"}


@app.get("/vendor-dashboard")
def serve_vendor_dashboard():
    path = os.path.join(os.path.dirname(__file__), "vendor_dashboard.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "vendor_dashboard.html file not found"}


@app.get("/dashboard")
def serve_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "vendor_dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {"error": "vendor_dashboard.html file not found"}
