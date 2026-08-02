from fastapi.testclient import TestClient
from main import app
from clear_products import clear_products_and_transactions

client = TestClient(app)


def test_fresh_product_sale_and_revenue_recalculation():
    print("🧪 Testing Fresh Product Creation, Sale Recording & Revenue Recalculation...\n")

    # Step 1: Clear products and transactions
    clear_products_and_transactions()

    # Step 2: Verify stats show 0 revenue when clean
    stats_empty = client.get("/stats").json()
    assert stats_empty["total_revenue"] == 0.0
    assert stats_empty["total_transactions"] == 0
    print("  ✓ Empty state verified: Total Revenue = ₹0.00, 0 transactions.")

    # Step 3: Login as Samsung (Vendor ID 2) & Add a fresh product
    login_res = client.post("/login", json={"email": "contact@samsung.com", "password": "vendor123"})
    assert login_res.status_code == 200
    samsung_id = login_res.json()["vendor_id"]

    create_prod_res = client.post("/products", json={
        "vendor_id": samsung_id,
        "name": "Galaxy S24 Ultra 5G",
        "price": 129999.00,
        "stock_qty": 20,
        "description": "Flagship smartphone with AI features and 200MP camera.",
        "category": "VISION: Electronics",
        "tags": "#GalaxyS24,#Flagship,#Samsung"
    })
    assert create_prod_res.status_code == 201
    prod_data = create_prod_res.json()
    prod_id = prod_data["id"]
    print(f"  ✓ Fresh Product Created: '{prod_data['name']}' (ID #{prod_id}, Price: ₹{prod_data['price']:,.2f}).")

    # Step 4: Record Sale ("Simulate Sale" endpoint)
    sale_res = client.post(f"/products/{prod_id}/simulate-sale")
    assert sale_res.status_code == 200
    sale_data = sale_res.json()
    assert sale_data["sale_amount"] == 129999.00
    assert sale_data["remaining_stock"] == 19
    print(f"  ✓ Sale Recorded! 1 unit sold for ₹{sale_data['sale_amount']:,.2f} (Remaining stock: {sale_data['remaining_stock']}).")

    # Step 5: Verify Global Platform Stats & Vendor of the Month Recalculation
    stats_after = client.get("/stats").json()
    assert stats_after["total_revenue"] == 129999.00
    assert stats_after["total_transactions"] == 1
    assert stats_after["top_vendor"]["name"] == "Samsung"
    assert stats_after["top_vendor"]["revenue"] == 129999.00
    assert stats_after["top_vendor"]["orders"] == 1
    print(f"  ✓ Total Platform Revenue updated: ₹{stats_after['total_revenue']:,.2f}")
    print(f"  ✓ Vendor of the Month recalculated: {stats_after['top_vendor']['name']} (₹{stats_after['top_vendor']['revenue']:,.2f} • {stats_after['top_vendor']['orders']} order)")

    # Step 6: Verify Per-Vendor Revenue Breakdown Endpoint
    revenue_summary = client.get("/vendors/revenue-summary").json()
    samsung_summary = next(v for v in revenue_summary if v["vendor_id"] == samsung_id)
    assert samsung_summary["total_revenue"] == 129999.00
    assert samsung_summary["total_orders"] == 1
    assert samsung_summary["total_units_sold"] == 1
    print(f"  ✓ Per-Vendor Financial Breakdown verified: {samsung_summary['vendor_name']} Total Revenue: ₹{samsung_summary['total_revenue']:,.2f}")

    # Step 7: Verify Live Activity Feed Timestamps & Order
    activity_feed = client.get("/activity-feed").json()
    latest_event = activity_feed[0]
    assert "Sale recorded: Samsung sold 1x 'Galaxy S24 Ultra 5G'" in latest_event["description"]
    assert "timestamp" in latest_event
    print(f"  ✓ Live Activity Feed verified! Latest Event: '{latest_event['description']}' at {latest_event['timestamp']}")

    print("\n🎉 FRESH PRODUCT & SALE REVENUE RECALCULATION VERIFIED 100% WORKING!")


if __name__ == "__main__":
    test_fresh_product_sale_and_revenue_recalculation()
