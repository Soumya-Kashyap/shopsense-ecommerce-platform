from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def run_full_suite_verification():
    print("==========================================================================")
    print("🧪 SHOP SENSE MILESTONE 2: FULL SUITE (ANALYTICS, SENTIMENT, RESTOCK & TRENDS)")
    print("==========================================================================\n")

    results_summary = []

    # --------------------------------------------------------------------------
    # 1. WEB ROUTE ACCESSIBILITY
    # --------------------------------------------------------------------------
    try:
        assert client.get("/login-page").status_code == 200
        assert client.get("/admin-dashboard").status_code == 200
        assert client.get("/vendor-dashboard").status_code == 200
        print("  ✓ Web Page routes (/login-page, /admin-dashboard, /vendor-dashboard) accessible.")
    except Exception as e:
        print(f"  ❌ Web Page routes check failed: {e}")
        raise

    # --------------------------------------------------------------------------
    # 2. VALIDATION CHECK 1: GET /inventory/low-stock
    # --------------------------------------------------------------------------
    print("\n--- [CHECK 1] GET /inventory/low-stock Validation ---")
    try:
        low_stock_res = client.get("/inventory/low-stock")
        assert low_stock_res.status_code == 200, f"Expected 200, got {low_stock_res.status_code}"
        low_stock_items = low_stock_res.json()

        for p in low_stock_items:
            assert p["stock_qty"] < 10, f"Product {p['product_name']} has stock {p['stock_qty']} >= 10 in low-stock endpoint!"

        expected_low_stock_count = 1
        assert len(low_stock_items) == expected_low_stock_count, f"Expected {expected_low_stock_count} low-stock items, found {len(low_stock_items)}"

        item_names = ", ".join([p["product_name"] for p in low_stock_items])
        print(f"  ✓ Every returned product has stock_qty < 10 ({item_names}: {low_stock_items[0]['stock_qty']} units).")
        print(f"  ✓ Total low-stock count ({len(low_stock_items)}) matches exact seeded low-stock count ({expected_low_stock_count}).")
        results_summary.append(("CHECK 1: GET /inventory/low-stock", "PASS"))
    except Exception as e:
        print(f"  ❌ CHECK 1 FAILED: {e}")
        results_summary.append(("CHECK 1: GET /inventory/low-stock", "FAIL"))
        raise

    # --------------------------------------------------------------------------
    # 3. VALIDATION CHECK 2: GET /customers/segments
    # --------------------------------------------------------------------------
    print("\n--- [CHECK 2] GET /customers/segments Validation ---")
    try:
        segments_res = client.get("/customers/segments")
        assert segments_res.status_code == 200, f"Expected 200, got {segments_res.status_code}"
        segments_data = segments_res.json()

        rahul = next((c for c in segments_data if "Rahul" in c["customer_name"]), None)
        assert rahul is not None, "Rahul Sharma not found in customer segments"
        assert rahul["segment"] == "High Value", f"Expected 'High Value' for Rahul, got {rahul['segment']}"
        assert rahul["total_spend"] >= 100000.0, f"Expected total_spend >= 100000, got {rahul['total_spend']}"

        priya = next((c for c in segments_data if "Priya" in c["customer_name"]), None)
        assert priya is not None, "Priya Patel not found in customer segments"
        assert priya["segment"] == "Medium Value", f"Expected 'Medium Value' for Priya, got {priya['segment']}"
        assert 25000.0 <= priya["total_spend"] < 100000.0, f"Expected spend between 25k-100k, got {priya['total_spend']}"

        vikram = next((c for c in segments_data if "Vikram" in c["customer_name"]), None)
        assert vikram is not None, "Vikram Singh not found in customer segments"
        assert vikram["segment"] == "Low Value", f"Expected 'Low Value' for Vikram, got {vikram['segment']}"
        assert vikram["total_spend"] < 25000.0, f"Expected spend < 25000, got {vikram['total_spend']}"

        print(f"  ✓ High Value: {rahul['customer_name']} (Spend: ₹{rahul['total_spend']:,.2f} >= ₹1,00,000) -> Classified as 'High Value'")
        print(f"  ✓ Medium Value: {priya['customer_name']} (Spend: ₹{priya['total_spend']:,.2f} in ₹25k-₹100k) -> Classified as 'Medium Value'")
        print(f"  ✓ Low Value: {vikram['customer_name']} (Spend: ₹{vikram['total_spend']:,.2f} < ₹25,000) -> Classified as 'Low Value'")
        results_summary.append(("CHECK 2: GET /customers/segments", "PASS"))
    except Exception as e:
        print(f"  ❌ CHECK 2 FAILED: {e}")
        results_summary.append(("CHECK 2: GET /customers/segments", "FAIL"))
        raise

    # --------------------------------------------------------------------------
    # 4. VALIDATION CHECK 3: GET /products/top-selling
    # --------------------------------------------------------------------------
    print("\n--- [CHECK 3] GET /products/top-selling Validation ---")
    try:
        top_res = client.get("/products/top-selling?limit=5")
        assert top_res.status_code == 200, f"Expected 200, got {top_res.status_code}"
        top_products = top_res.json()
        assert len(top_products) > 0, "No top-selling products returned"

        units_sold_list = [p["units_sold"] for p in top_products]
        assert units_sold_list == sorted(units_sold_list, reverse=True), f"Products not sorted descending by units_sold: {units_sold_list}"

        max_units = max(units_sold_list)
        assert top_products[0]["units_sold"] == max_units, f"Top product units_sold ({top_products[0]['units_sold']}) != max units_sold ({max_units})"

        top_item = top_products[0]
        print(f"  ✓ Products sorted descending by units_sold: {units_sold_list}")
        print(f"  ✓ Top product '#1 {top_item['product_name']}' has maximum units_sold ({top_item['units_sold']} units, ₹{top_item['total_revenue']:,.2f}).")
        results_summary.append(("CHECK 3: GET /products/top-selling", "PASS"))
    except Exception as e:
        print(f"  ❌ CHECK 3 FAILED: {e}")
        results_summary.append(("CHECK 3: GET /products/top-selling", "FAIL"))
        raise

    # --------------------------------------------------------------------------
    # 5. VALIDATION CHECK 4: SENTIMENT ANALYSIS & CUSTOMER REVIEWS
    # --------------------------------------------------------------------------
    print("\n--- [CHECK 4] Customer Reviews & Sentiment Analysis Validation ---")
    try:
        overview_res = client.get("/inventory/overview")
        assert overview_res.status_code == 200
        p_id = overview_res.json()[0]["product_id"]

        pos_payload = {
            "customer_name": "TestSuite Reviewer",
            "review_text": "Absolutely amazing product! Excellent sound quality, fantastic battery life, love it!",
            "rating": 5
        }
        post_res = client.post(f"/products/{p_id}/reviews", json=pos_payload)
        assert post_res.status_code == 201, f"Expected 201, got {post_res.status_code}"
        created_rev = post_res.json()
        assert created_rev["sentiment_label"] == "Positive", f"Expected Positive, got {created_rev['sentiment_label']}"

        get_res = client.get(f"/products/{p_id}/reviews")
        assert get_res.status_code == 200
        data = get_res.json()
        agg = data["aggregate"]

        print(f"  ✓ POST /products/{p_id}/reviews verified! Sentiment analyzed as '{created_rev['sentiment_label']}' (Score: {created_rev['sentiment_score']}).")
        print(f"  ✓ GET /products/{p_id}/reviews verified! Aggregate Rating: {agg['average_rating']}★, {agg['positive_percentage']}% Positive.")
        results_summary.append(("CHECK 4: Reviews & Sentiment Analysis", "PASS"))
    except Exception as e:
        print(f"  ❌ CHECK 4 FAILED: {e}")
        results_summary.append(("CHECK 4: Reviews & Sentiment Analysis", "FAIL"))
        raise

    # --------------------------------------------------------------------------
    # 6. VALIDATION CHECK 5: RESTOCK INVENTORY ENDPOINT
    # --------------------------------------------------------------------------
    print("\n--- [CHECK 5] POST /products/{product_id}/restock Validation ---")
    try:
        low_res = client.get("/inventory/low-stock")
        assert low_res.status_code == 200
        low_items = low_res.json()
        assert len(low_items) > 0, "No low-stock item found to test restock!"

        target = low_items[0]
        t_id = target["product_id"]
        initial_stock = target["stock_qty"]
        add_qty = 20

        restock_res = client.post(f"/products/{t_id}/restock", json={"quantity": add_qty})
        assert restock_res.status_code == 200, f"Expected 200, got {restock_res.status_code}"
        restock_data = restock_res.json()

        expected_new_stock = initial_stock + add_qty
        assert restock_data["new_stock_qty"] == expected_new_stock, f"Expected {expected_new_stock}, got {restock_data['new_stock_qty']}"

        # Verify low-stock list is updated (should now be 0 since stock >= 10)
        new_low_res = client.get("/inventory/low-stock")
        assert new_low_res.status_code == 200
        new_low_items = new_low_res.json()
        assert not any(p["product_id"] == t_id for p in new_low_items), f"Product #{t_id} still listed in low-stock after restock!"

        print(f"  ✓ Restocked Product #{t_id} '{target['product_name']}' from {initial_stock} -> {expected_new_stock} units.")
        print(f"  ✓ Verified product clears 'Low Stock' flag after restocking above 10 units.")
        results_summary.append(("CHECK 5: POST /products/{id}/restock", "PASS"))
    except Exception as e:
        print(f"  ❌ CHECK 5 FAILED: {e}")
        results_summary.append(("CHECK 5: POST /products/{id}/restock", "FAIL"))
        raise

    # --------------------------------------------------------------------------
    # 7. VALIDATION CHECK 6: GET /analytics/sales-trend
    # --------------------------------------------------------------------------
    print("\n--- [CHECK 6] GET /analytics/sales-trend Validation ---")
    try:
        trend_res = client.get("/analytics/sales-trend")
        assert trend_res.status_code == 200, f"Expected 200, got {trend_res.status_code}"
        trend_data = trend_res.json()

        assert len(trend_data) == 7, f"Expected 7 daily items, got {len(trend_data)}"
        for item in trend_data:
            assert "date" in item and "day_label" in item and "revenue" in item and "orders" in item
            assert item["revenue"] >= 0.0

        today_item = trend_data[-1]
        print(f"  ✓ Returned 7 daily revenue data points: {[d['day_label'] for d in trend_data]}")
        print(f"  ✓ Today ({today_item['day_label']} {today_item['date']}): Revenue ₹{today_item['revenue']:,.2f} ({today_item['orders']} orders).")
        results_summary.append(("CHECK 6: GET /analytics/sales-trend", "PASS"))
    except Exception as e:
        print(f"  ❌ CHECK 6 FAILED: {e}")
        results_summary.append(("CHECK 6: GET /analytics/sales-trend", "FAIL"))
        raise

    # --------------------------------------------------------------------------
    # 8. SUMMARY REPORT
    # --------------------------------------------------------------------------
    print("\n==========================================================================")
    print("📋 MILESTONE 2 ANALYTICAL, SENTIMENT, RESTOCK & TRENDS SUMMARY")
    print("==========================================================================")
    all_passed = True
    for check_name, status_str in results_summary:
        symbol = "✅" if status_str == "PASS" else "❌"
        print(f"  {symbol} {check_name}: [{status_str}]")
        if status_str != "PASS":
            all_passed = False

    print("==========================================================================")
    if all_passed:
        print("🎉 ALL MILESTONE 2 VALIDATION CHECKS PASSED SUCCESSFULLY!")
    else:
        print("❌ SOME VALIDATION CHECKS FAILED.")
    print("==========================================================================")


if __name__ == "__main__":
    run_full_suite_verification()
