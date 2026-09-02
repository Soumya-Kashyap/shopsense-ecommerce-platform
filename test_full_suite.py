from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def run_full_suite_verification():
    print("==========================================================================")
    print("🧪 SHOP SENSE MILESTONE 3: FULL SUITE (ANALYTICS, SENTIMENT, WEBSOCKETS, RAG, TEXT-TO-SQL & PDF)")
    print("==========================================================================\n")

    results_summary = []

    # --------------------------------------------------------------------------
    # 1. WEB ROUTE ACCESSIBILITY
    # --------------------------------------------------------------------------
    try:
        assert client.get("/login-page").status_code == 200
        assert client.get("/admin-dashboard").status_code == 200
        assert client.get("/vendor-dashboard").status_code == 200
        assert client.get("/shopping-assistant").status_code == 200
        print("  ✓ Web Page routes (/login-page, /admin-dashboard, /vendor-dashboard, /shopping-assistant) accessible.")
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
    # 8. VALIDATION CHECK 7: MILESTONE 3 CHART ENDPOINTS (/charts/*)
    # --------------------------------------------------------------------------
    print("\n--- [CHECK 7] Milestone 3 Chart Endpoints (/charts/*) Validation ---")
    try:
        assert client.get("/charts/revenue-by-vendor").status_code == 200
        assert client.get("/charts/daily-orders-trend").status_code == 200
        assert client.get("/charts/customer-segment-distribution").status_code == 200
        assert client.get("/charts/category-sales-breakdown").status_code == 200

        print(f"  ✓ All 4 /charts/* endpoints verified.")
        results_summary.append(("CHECK 7: /charts/* Endpoints", "PASS"))
    except Exception as e:
        print(f"  ❌ CHECK 7 FAILED: {e}")
        results_summary.append(("CHECK 7: /charts/* Endpoints", "FAIL"))
        raise

    # --------------------------------------------------------------------------
    # 9. VALIDATION CHECK 8: MILESTONE 3 BENCHMARKING ENDPOINT
    # --------------------------------------------------------------------------
    print("\n--- [CHECK 8] GET /analytics/benchmarks Validation ---")
    try:
        bm_res = client.get("/analytics/benchmarks")
        assert bm_res.status_code == 200
        bm_data = bm_res.json()
        assert "marketplace_averages" in bm_data and "vendors" in bm_data
        print(f"  ✓ GET /analytics/benchmarks verified.")
        results_summary.append(("CHECK 8: GET /analytics/benchmarks", "PASS"))
    except Exception as e:
        print(f"  ❌ CHECK 8 FAILED: {e}")
        results_summary.append(("CHECK 8: GET /analytics/benchmarks", "FAIL"))
        raise

    # --------------------------------------------------------------------------
    # 10. VALIDATION CHECK 9: MILESTONE 3 CSV EXPORTS
    # --------------------------------------------------------------------------
    print("\n--- [CHECK 9] CSV Reports & Sales Exports Validation ---")
    try:
        r1 = client.get("/reports/export/vendors-csv")
        assert r1.status_code == 200
        r2 = client.get("/products/1/export/sales-csv")
        assert r2.status_code == 200
        print(f"  ✓ CSV Export endpoints (/reports/export/vendors-csv & /products/1/export/sales-csv) verified.")
        results_summary.append(("CHECK 9: CSV Export Endpoints", "PASS"))
    except Exception as e:
        print(f"  ❌ CHECK 9 FAILED: {e}")
        results_summary.append(("CHECK 9: CSV Export Endpoints", "FAIL"))
        raise

    # --------------------------------------------------------------------------
    # 11. VALIDATION CHECK 10: MILESTONE 3 WEBSOCKET NOTIFICATIONS
    # --------------------------------------------------------------------------
    print("\n--- [CHECK 10] WebSocket Real-Time Notifications (/ws/notifications) Validation ---")
    try:
        with client.websocket_connect("/ws/notifications") as websocket:
            sale_res = client.post("/products/1/simulate-sale")
            assert sale_res.status_code == 200
            msg_payload = websocket.receive_json()
            assert msg_payload["event"] == "new_sale"
            print(f"  ✓ WebSocket broadcast received: {msg_payload['vendor_name']} sold '{msg_payload['product_name']}'.")
        results_summary.append(("CHECK 10: WS Real-Time Notifications", "PASS"))
    except Exception as e:
        print(f"  ❌ CHECK 10 FAILED: {e}")
        results_summary.append(("CHECK 10: WS Real-Time Notifications", "FAIL"))
        raise

    # --------------------------------------------------------------------------
    # 12. VALIDATION CHECK 11: MILESTONE 3 RAG AI SHOPPING ASSISTANT
    # --------------------------------------------------------------------------
    print("\n--- [CHECK 11] RAG AI Shopping Assistant (POST /assistant/ask) Validation ---")
    try:
        ask_payload = {"question": "What are the best wireless earbuds under 15000?"}
        ask_res = client.post("/assistant/ask", json=ask_payload)
        assert ask_res.status_code == 200, f"Expected 200, got {ask_res.status_code}"
        res_data = ask_res.json()

        assert "answer" in res_data and "matched_products" in res_data and "fallback_used" in res_data
        assert isinstance(res_data["answer"], str) and len(res_data["answer"]) > 10
        assert len(res_data["matched_products"]) > 0

        first_p = res_data["matched_products"][0]
        assert first_p["price"] <= 15000.0

        print(f"  ✓ POST /assistant/ask verified!")
        print(f"  ✓ LLM Response Generated ({len(res_data['answer'])} chars): \"{res_data['answer'][:120]}...\"")
        print(f"  ✓ Matched Real Products: {len(res_data['matched_products'])} item(s).")
        results_summary.append(("CHECK 11: RAG AI Shopping Assistant", "PASS"))
    except Exception as e:
        print(f"  ❌ CHECK 11 FAILED: {e}")
        results_summary.append(("CHECK 11: RAG AI Shopping Assistant", "FAIL"))
        raise

    # --------------------------------------------------------------------------
    # 13. VALIDATION CHECK 12: MILESTONE 3 AI DATA ANALYST (TEXT-TO-SQL)
    # --------------------------------------------------------------------------
    print("\n--- [CHECK 12] AI Data Analyst Text-to-SQL (POST /vendor/{id}/ai-analyst) Validation ---")
    try:
        analyst_payload = {"question": "What is my top selling product by units sold?"}
        analyst_res = client.post("/vendor/1/ai-analyst", json=analyst_payload)
        assert analyst_res.status_code == 200, f"Expected 200, got {analyst_res.status_code}"
        analyst_data = analyst_res.json()

        assert "answer" in analyst_data and "sql_query" in analyst_data and "data" in analyst_data
        assert analyst_data["query_success"] is True
        assert "SELECT" in analyst_data["sql_query"].upper() or "WITH" in analyst_data["sql_query"].upper()

        print(f"  ✓ POST /vendor/1/ai-analyst verified!")
        print(f"  ✓ Text-to-SQL Query Generated: {analyst_data['sql_query']}")
        print(f"  ✓ Natural Language Answer: \"{analyst_data['answer'][:120]}...\"")
        results_summary.append(("CHECK 12: AI Data Analyst (Text-to-SQL)", "PASS"))
    except Exception as e:
        print(f"  ❌ CHECK 12 FAILED: {e}")
        results_summary.append(("CHECK 12: AI Data Analyst (Text-to-SQL)", "FAIL"))
        raise

    # --------------------------------------------------------------------------
    # 14. VALIDATION CHECK 13: PDF REPORT EXPORT (GET /reports/export/vendors-pdf)
    # --------------------------------------------------------------------------
    print("\n--- [CHECK 13] PDF Report Export (GET /reports/export/vendors-pdf) Validation ---")
    try:
        pdf_res = client.get("/reports/export/vendors-pdf")
        assert pdf_res.status_code == 200, f"Expected 200, got {pdf_res.status_code}"
        assert pdf_res.headers.get("content-type") == "application/pdf"
        assert pdf_res.content.startswith(b"%PDF-"), "Downloaded file does not start with valid PDF magic bytes %PDF-"

        print(f"  ✓ GET /reports/export/vendors-pdf verified!")
        print(f"  ✓ Valid PDF document generated ({len(pdf_res.content)} bytes, Content-Type: application/pdf).")
        results_summary.append(("CHECK 13: PDF Report Export", "PASS"))
    except Exception as e:
        print(f"  ❌ CHECK 13 FAILED: {e}")
        results_summary.append(("CHECK 13: PDF Report Export", "FAIL"))
        raise

    # --------------------------------------------------------------------------
    # 15. SUMMARY REPORT
    # --------------------------------------------------------------------------
    print("\n==========================================================================")
    print("📋 MILESTONE 3 FULL SUITE VALIDATION SUMMARY")
    print("==========================================================================")
    all_passed = True
    for check_name, status_str in results_summary:
        symbol = "✅" if status_str == "PASS" else "❌"
        print(f"  {symbol} {check_name}: [{status_str}]")
        if status_str != "PASS":
            all_passed = False

    print("==========================================================================")
    if all_passed:
        print("🎉 ALL MILESTONE 3 VALIDATION CHECKS PASSED SUCCESSFULLY!")
    else:
        print("❌ SOME VALIDATION CHECKS FAILED.")
    print("==========================================================================")


if __name__ == "__main__":
    run_full_suite_verification()
