from fastapi.testclient import TestClient
from main import app
from database import SessionLocal, engine, Base
import models

# Initialize test client
client = TestClient(app)


def test_full_shopsense_flow():
    # 1. Ensure clean tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # 2. Test Vendor Registration (POST /vendors/register)
    vendor_payload = {
        "name": "TechWorld Store",
        "email": "vendor@techworld.com",
        "phone": "+1-555-0100"
    }
    response = client.post("/vendors/register", json=vendor_payload)
    assert response.status_code == 201
    vendor_data = response.json()
    assert vendor_data["id"] == 1
    assert vendor_data["name"] == "TechWorld Store"
    assert vendor_data["email"] == "vendor@techworld.com"
    print("✅ Vendor Registration Endpoint (POST /vendors/register) passed!")

    # 3. Test Duplicate Registration (Validation error)
    response_dup = client.post("/vendors/register", json=vendor_payload)
    assert response_dup.status_code == 400
    print("✅ Duplicate Email Validation passed!")

    # 4. Test Get Vendor Profile (GET /vendors/1)
    response_get = client.get("/vendors/1")
    assert response_get.status_code == 200
    assert response_get.json()["name"] == "TechWorld Store"
    print("✅ Get Vendor Profile Endpoint (GET /vendors/{id}) passed!")

    # 5. Test Update Vendor Profile (PUT /vendors/1)
    update_payload = {"phone": "+1-555-9999", "name": "TechWorld Global"}
    response_put = client.put("/vendors/1", json=update_payload)
    assert response_put.status_code == 200
    assert response_put.json()["phone"] == "+1-555-9999"
    assert response_put.json()["name"] == "TechWorld Global"
    print("✅ Update Vendor Profile Endpoint (PUT /vendors/{id}) passed!")

    # 6. Seed Product, Customer, and Transaction data directly in DB for analytics test
    db = SessionLocal()
    try:
        # Create 2 Products for Vendor 1
        p1 = models.Product(vendor_id=1, name="Gaming Laptop", price=1200.0, stock_qty=10)
        p2 = models.Product(vendor_id=1, name="Wireless Headphones", price=150.0, stock_qty=30)
        db.add_all([p1, p2])
        db.commit()

        # Create Customer
        c1 = models.Customer(name="Alice Smith", email="alice@example.com")
        db.add(c1)
        db.commit()

        # Create 2 Transactions for Vendor 1's products
        t1 = models.Transaction(customer_id=c1.id, product_id=p1.id, quantity=2, total_amount=2400.0)
        t2 = models.Transaction(customer_id=c1.id, product_id=p2.id, quantity=3, total_amount=450.0)
        db.add_all([t1, t2])
        db.commit()
    finally:
        db.close()

    # 7. Test Vendor Sales Analytics Endpoint (GET /vendors/1/sales)
    response_sales = client.get("/vendors/1/sales")
    assert response_sales.status_code == 200
    sales_data = response_sales.json()
    assert sales_data["vendor_id"] == 1
    assert sales_data["total_orders"] == 2
    assert sales_data["total_units_sold"] == 5
    assert sales_data["total_revenue"] == 2850.0
    print("✅ Vendor Sales Analytics Endpoint (GET /vendors/{id}/sales with Pandas) passed!")


if __name__ == "__main__":
    test_full_shopsense_flow()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
