import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

import models
import schemas
from database import engine, get_db, SessionLocal
from routers import vendors, products, inventory, customers, reviews, analytics, charts, reports, notifications, assistant, analyst
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
    version="3.4.0"
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
app.include_router(inventory.router)
app.include_router(customers.router)
app.include_router(reviews.router)
app.include_router(analytics.router)
app.include_router(charts.router)
app.include_router(reports.router)
app.include_router(notifications.router)
app.include_router(assistant.router)
app.include_router(analyst.router)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to ShopSense API: Multi-Vendor E-Commerce Analytics Platform",
        "docs_url": "http://127.0.0.1:8000/docs",
        "login_url": "http://127.0.0.1:8000/login-page",
        "admin_dashboard_url": "http://127.0.0.1:8000/admin-dashboard",
        "vendor_dashboard_url": "http://127.0.0.1:8000/vendor-dashboard",
        "shopping_assistant_url": "http://127.0.0.1:8000/shopping-assistant",
        "currency": "INR (₹)",
        "milestone": "Milestone 3 - RAG AI Assistant, WebSockets, Charts & Benchmarking"
    }


@app.get("/stats")
def get_global_stats(db: Session = Depends(get_db)):
    """
    Analytics Endpoint: Global platform metrics, revenue in ₹ INR, and Top Vendor of the Month.
    """
    active_vendors_count = db.query(models.Vendor).filter(models.Vendor.status == "active", models.Vendor.role == "vendor").count()
    pending_vendors_count = db.query(models.Vendor).filter(models.Vendor.status == "pending", models.Vendor.role == "vendor").count()

    total_revenue = db.query(func.sum(models.Transaction.total_amount)).scalar() or 0.0

    top_vendor_query = (
        db.query(
            models.Vendor.id,
            models.Vendor.name,
            func.sum(models.Transaction.total_amount).label("revenue"),
            func.count(models.Transaction.id).label("orders")
        )
        .join(models.Product, models.Product.vendor_id == models.Vendor.id)
        .join(models.Transaction, models.Transaction.product_id == models.Product.id)
        .group_by(models.Vendor.id, models.Vendor.name)
        .order_by(desc("revenue"))
        .first()
    )

    top_vendor_data = None
    if top_vendor_query:
        top_vendor_data = {
            "id": top_vendor_query.id,
            "name": top_vendor_query.name,
            "revenue": float(top_vendor_query.revenue),
            "orders": int(top_vendor_query.orders)
        }

    return {
        "active_vendors": active_vendors_count,
        "pending_vendors": pending_vendors_count,
        "total_revenue": float(total_revenue),
        "top_vendor": top_vendor_data
    }


@app.get("/activity-feed", response_model=list[schemas.ActivityLogResponse])
def get_activity_feed(limit: int = 15, db: Session = Depends(get_db)):
    """
    LIVE ACTIVITY FEED ENDPOINT:
    Returns the most recent system activity logs sorted by timestamp descending.
    """
    logs = db.query(models.ActivityLog).order_by(models.ActivityLog.timestamp.desc()).limit(limit).all()
    return logs


# ==========================================
# PUBLIC WEB PAGE ROUTES
# ==========================================

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


@app.get("/shopping-assistant")
def serve_shopping_assistant():
    path = os.path.join(os.path.dirname(__file__), "shopping_assistant.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "shopping_assistant.html file not found"}


@app.get("/dashboard")
def serve_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "vendor_dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {"error": "vendor_dashboard.html file not found"}
