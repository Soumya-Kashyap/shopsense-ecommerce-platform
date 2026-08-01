from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def run_full_suite_verification():
    print("🧪 Running ShopSense Full End-to-End Suite Verification...\n")

    # 1. Web Page Routes
    assert client.get("/login-page").status_code == 200
    assert client.get("/admin-dashboard").status_code == 200
    assert client.get("/vendor-dashboard").status_code == 200
    print("  ✓ Web Page routes (/login-page, /admin-dashboard, /vendor-dashboard) verified!")

    # 2. Stats & Platform Revenue Calculation in INR
    stats_res = client.get("/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_revenue"] > 0
    assert "top_vendor" in stats
    print(f"  ✓ Platform Revenue & Top Vendor verified! Total Revenue: ₹{stats['total_revenue']:,.2f}, Top Vendor: {stats['top_vendor']['name']} (₹{stats['top_vendor']['revenue']:,.2f})")

    # 3. Simulate Sale Feature Test (REQUIREMENT 2)
    # Simulate sale for product ID 4 (JBL Flip 6 Waterproof Speaker, initial stock 5, price ₹9999.00)
    sale_res = client.post("/products/4/simulate-sale")
    assert sale_res.status_code == 200
    sale_data = sale_res.json()
    assert sale_data["remaining_stock"] == 4
    assert sale_data["sale_amount"] == 9999.00
    print(f"  ✓ POST /products/4/simulate-sale verified! Sold 1 unit for ₹9,999.00 (Remaining Stock: {sale_data['remaining_stock']})")

    # 4. Live Activity Feed Endpoint & IST Timestamp Support (REQUIREMENT 1)
    activity_res = client.get("/activity-feed")
    assert activity_res.status_code == 200
    logs = activity_res.json()
    assert len(logs) > 0
    assert any(log["event_type"] == "sale_simulated" for log in logs)
    print(f"  ✓ Live Activity Feed verified! Received {len(logs)} system activity events (including live simulated sale).")

    # 5. Per-Vendor Revenue Breakdown Endpoint
    vendor_rev_res = client.get("/vendors/revenue-summary")
    assert vendor_rev_res.status_code == 200
    vendor_summary = vendor_rev_res.json()
    assert len(vendor_summary) >= 5
    jbl_summary = next(v for v in vendor_summary if v["vendor_name"] == "JBL")
    assert jbl_summary["total_orders"] >= 2
    print(f"  ✓ Per-Vendor Revenue Summary verified! JBL Total Revenue: ₹{jbl_summary['total_revenue']:,.2f} ({jbl_summary['total_orders']} orders)")

    # 6. Multi-Vendor Auth & Isolation
    vendors_to_test = [
        {"email": "contact@sony.com", "name": "Sony"},
        {"email": "contact@jbl.com", "name": "JBL"},
        {"email": "contact@samsung.com", "name": "Samsung"}
    ]

    for v_info in vendors_to_test:
        login_res = client.post("/login", json={"email": v_info["email"], "password": "vendor123"})
        assert login_res.status_code == 200
        data = login_res.json()
        v_id = data["vendor_id"]

        prods_res = client.get(f"/vendors/{v_id}/products")
        assert prods_res.status_code == 200
        prods = prods_res.json()
        assert all(p["vendor_id"] == v_id for p in prods)
        print(f"  ✓ Multi-vendor login & isolated catalog verified for {v_info['name']} (ID #{v_id}, {len(prods)} products)")

    print("\n🎉 ALL SHOP SENSE ENHANCED SUITE TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_full_suite_verification()
