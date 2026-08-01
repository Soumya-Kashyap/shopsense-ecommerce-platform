
# ShopSense — Multi-Vendor E-Commerce Analytics Platform

A full-stack multi-vendor marketplace platform with role-based authentication, vendor management, and AI-simulated product enrichment — built as part of the Infosys Springboard internship program.

## 🚀 Overview

ShopSense allows multiple vendors to register, list products, and track their own sales, while a platform admin oversees vendor approvals, monitors platform-wide revenue, and manages the marketplace — all through two dedicated dashboards.

## 🛠 Tech Stack

**Backend**
- Python
- FastAPI
- SQLAlchemy (ORM)
- SQLite (database)
- Pandas (sales analytics)
- Passlib / bcrypt (password hashing)

**Frontend**
- HTML, CSS, JavaScript (vanilla — no frameworks)
- Dark-themed SaaS-style UI with glassmorphism and animations

## ✨ Features

### Authentication
- Role-based login (Admin / Vendor) through a single portal
- Passwords hashed with bcrypt — never stored in plain text
- Session handling via access tokens

### Admin Dashboard
- Platform-wide stats: total revenue (₹ INR), active vendors, pending approvals
- Vendor Directory with Approve / Reject / Set Pending controls
- Register new vendors directly from the dashboard
- Per-Vendor Revenue & Financial Breakdown table
- 🏆 Vendor of the Month — auto-calculated from real transaction data
- Live Activity Feed — tracks real platform events in real time
- Vendor Status Matrix Breakdown (Active / Pending / Rejected)

### Vendor Dashboard
- Vendor-only login showing only their own product catalog
- Add New Product form with image upload
- AI-simulated product enrichment:
  - Auto-generated SEO-optimized descriptions
  - Auto-generated keyword tags
  - Vision-based category prediction
- Low Stock alerts for inventory below threshold
- Record Sale — simulates a real transaction for demo/testing purposes
- AI Marketing Studio — generates a promotional email per product

## 📊 Database Schema

Four core tables with relational integrity:
- **Vendors** — id, name, email, password (hashed), role, status
- **Products** — id, vendor_id (FK), name, price, stock_qty, description, tags, category, image
- **Customers** — id, name, email
- **Transactions** — id, customer_id (FK), product_id (FK), quantity, total_amount

## 📁 Project Structure

```
shopsense/
├── main.py                 # FastAPI entry point
├── models.py                # SQLAlchemy database models
├── schemas.py                # Pydantic validation schemas
├── database.py               # DB connection & session handling
├── auth.py                  # Authentication logic
├── seed_data.py               # Sample data seeding script
├── routers/
│   ├── vendors.py             # Vendor-related API endpoints
│   └── products.py            # Product-related API endpoints
├── login.html                # Login page (Admin + Vendor)
├── admin_dashboard.html          # Admin Control Dashboard
├── vendor_dashboard.html         # Vendor Merchant Portal
└── requirements.txt             # Python dependencies
```

## ⚙️ Running Locally

1. Clone the repository
```bash
git clone https://github.com/Soumya-Kashyap/shopsense-ecommerce-platform.git
cd shopsense-ecommerce-platform
```

2. Set up a virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Seed sample data
```bash
python seed_data.py
```

5. Start the server
```bash
uvicorn main:app --reload
```

6. Open the app
- API docs: `http://127.0.0.1:8000/docs`
- Login page: open `login.html` in your browser

### Demo Credentials
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@shopsense.com | admin |
| Vendor (Samsung) | contact@samsung.com | vendor123 |

## 📌 Project Status

**Milestone 1 — Marketplace Foundation & Vendor Analytics** ✅ Complete
- Database schema, REST APIs, sales analytics, and input validation implemented and tested
- Additional features built beyond base requirements: authentication, role-based dashboards, AI-simulated product enrichment, and real-time analytics

## 👩‍💻 Author

**Soumya Kashyap**
B.Tech CSE, Narula Institute of Technology
[GitHub](https://github.com/Soumya-Kashyap)
