import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

import models
import schemas
from auth import hash_password
from database import SessionLocal, engine, get_db
from routers import (
    analyst,
    analytics,
    assistant,
    charts,
    customers,
    inventory,
    notifications,
    products,
    reports,
    reviews,
    vendors,
)

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

# Initialize FastAPI application with comprehensive OpenAPI metadata
app = FastAPI(
    title="ShopSense Multi-Vendor E-Commerce Platform API",
    description="""
# 🛍️ ShopSense Multi-Vendor E-Commerce Analytics Platform API

Welcome to the **ShopSense REST & Real-Time API**. ShopSense is an enterprise-grade multi-vendor marketplace platform featuring:
* 🔐 **Role-Based Authentication**: Secure login for System Administrators and Vendors.
* 🏬 **Vendor Management**: Merchant onboarding, status controls (active/pending/suspended), and financial analytics.
* 📦 **Product Catalog & AI Enrichment**: Dynamic vision categorization, SEO tagging, and restock management.
* 📊 **Analytics & Benchmarking**: Marketplace baseline benchmarks, customer spend segmentation, and sales trend tracking.
* 💬 **Sentiment Analysis**: Customer product review aggregation and sentiment score calculation.
* ⚡ **Real-Time WebSockets**: Live broadcast of platform sales to administrative dashboards.
* 🤖 **RAG AI Shopping Assistant**: Natural language product recommendations powered by Groq LLM.
* 🧠 **AI Data Analyst**: Natural language Text-to-SQL business analytics for vendor merchants.
* 📑 **Executive Reporting**: Dynamic PDF & CSV export capabilities for platform metrics.

---
### 🔗 Useful Links
* **Web Login Portal**: `/login-page`
* **Admin Control Dashboard**: `/admin-dashboard`
* **Vendor Portal**: `/vendor-dashboard`
* **AI Shopping Assistant**: `/shopping-assistant`
    """,
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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


@app.get(
    "/",
    summary="API Root & Service Health Check",
    description="Returns welcome status message, platform currency, and operational navigation endpoints.",
    response_description="JSON dictionary containing service status and quick navigation URLs",
    tags=["Platform Overview & UI Portals"]
)
def read_root():
    return {
        "message": "Welcome to ShopSense API: Multi-Vendor E-Commerce Analytics Platform",
        "docs_url": "http://127.0.0.1:8000/docs",
        "login_url": "http://127.0.0.1:8000/login-page",
        "admin_dashboard_url": "http://127.0.0.1:8000/admin-dashboard",
        "vendor_dashboard_url": "http://127.0.0.1:8000/vendor-dashboard",
        "shopping_assistant_url": "http://127.0.0.1:8000/shopping-assistant",
        "currency": "INR (₹)",
        "milestone": "Milestone 4 - Docker Packaging, Optimization & Testing"
    }


@app.get(
    "/stats",
    summary="Global Platform Overview & Top Vendor Metrics",
    description="Calculates overall marketplace metrics including total platform revenue (₹ INR), active vendor count, pending approvals, and top vendor of the month.",
    response_description="Key platform performance stat object",
    tags=["Platform Overview & UI Portals"]
)
def get_global_stats(db: Session = Depends(get_db)):
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


@app.get(
    "/activity-feed",
    response_model=list[schemas.ActivityLogResponse],
    summary="Recent Platform Activity Stream",
    description="Retrieves the most recent system activity logs (vendor approvals, sale events, restock events) sorted by timestamp descending.",
    response_description="List of system activity log records",
    tags=["Platform Overview & UI Portals"]
)
def get_activity_feed(limit: int = 15, db: Session = Depends(get_db)):
    logs = db.query(models.ActivityLog).order_by(models.ActivityLog.timestamp.desc()).limit(limit).all()
    return logs


# ==========================================
# PUBLIC WEB PAGE ROUTES
# ==========================================

@app.get(
    "/login-page",
    summary="Serve Login Page HTML",
    description="Serves the single unified login web portal for Administrators and Vendors.",
    response_description="HTML document file response",
    tags=["Platform Overview & UI Portals"]
)
def serve_login_page():
    path = os.path.join(os.path.dirname(__file__), "login.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "login.html file not found"}


@app.get(
    "/admin-dashboard",
    summary="Serve Admin Dashboard HTML",
    description="Serves the administrative control dashboard web interface.",
    response_description="HTML document file response",
    tags=["Platform Overview & UI Portals"]
)
def serve_admin_dashboard():
    path = os.path.join(os.path.dirname(__file__), "admin_dashboard.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "admin_dashboard.html file not found"}


@app.get(
    "/vendor-dashboard",
    summary="Serve Vendor Portal HTML",
    description="Serves the merchant vendor dashboard portal web interface.",
    response_description="HTML document file response",
    tags=["Platform Overview & UI Portals"]
)
def serve_vendor_dashboard():
    path = os.path.join(os.path.dirname(__file__), "vendor_dashboard.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "vendor_dashboard.html file not found"}


@app.get(
    "/shopping-assistant",
    summary="Serve AI Shopping Assistant HTML",
    description="Serves the customer-facing AI Shopping Assistant chat web interface.",
    response_description="HTML document file response",
    tags=["Platform Overview & UI Portals"]
)
def serve_shopping_assistant():
    path = os.path.join(os.path.dirname(__file__), "shopping_assistant.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "shopping_assistant.html file not found"}


@app.get(
    "/dashboard",
    summary="Serve Vendor Dashboard (Alias)",
    description="Convenience route redirecting to the vendor dashboard interface.",
    response_description="HTML document file response",
    tags=["Platform Overview & UI Portals"]
)
def serve_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "vendor_dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {"error": "vendor_dashboard.html file not found"}
