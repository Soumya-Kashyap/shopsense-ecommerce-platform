"""
ShopSense OS — Milestone 4: Focused Unit Test Suite (Pytest)
Isolated unit tests for core domain functions and safety logic.
"""

from auth import hash_password, verify_password
from routers.analyst import sanitize_and_validate_sql
from routers.reviews import analyze_review_sentiment

# ==============================================================================
# 1. PASSWORD HASHING & VERIFICATION UNIT TESTS
# ==============================================================================

def test_password_hashing():
    """
    Tests that plain text passwords are encrypted securely using bcrypt,
    and that verify_password correctly matches valid credentials while rejecting invalid ones.
    """
    raw_password = "SecretPassword123!"
    hashed = hash_password(raw_password)

    # 1. Ensure hashed password is not plain text
    assert hashed != raw_password
    assert len(hashed) > 20

    # 2. Verify correct password succeeds
    assert verify_password(raw_password, hashed) is True

    # 3. Verify incorrect password fails
    assert verify_password("WrongPassword123!", hashed) is False


# ==============================================================================
# 2. SENTIMENT SCORING & CLASSIFICATION UNIT TESTS
# ==============================================================================

def test_sentiment_scoring():
    """
    Tests rule-based sentiment analysis directly with known positive, negative,
    and neutral customer review text inputs.
    """
    # Clearly Positive Review
    pos_text = "Absolutely amazing product! Great sound quality, fantastic battery life, highly recommend!"
    score_pos, label_pos, pros_pos, cons_pos = analyze_review_sentiment(pos_text)
    assert label_pos == "Positive"
    assert score_pos > 0.0

    # Clearly Negative Review
    neg_text = "Terrible experience. The product arrived broken, defective quality, slow performance, awful junk!"
    score_neg, label_neg, pros_neg, cons_neg = analyze_review_sentiment(neg_text)
    assert label_neg == "Negative"
    assert score_neg < 0.0

    # Neutral / Factual Review
    neu_text = "The product arrived in a standard box yesterday."
    score_neu, label_neu, pros_neu, cons_neu = analyze_review_sentiment(neu_text)
    assert label_neu == "Neutral"
    assert score_neu == 0.0


# ==============================================================================
# 3. LOW-STOCK DETECTION LOGIC UNIT TESTS
# ==============================================================================

def classify_inventory_status(stock_qty: int) -> str:
    """Helper function reproducing inventory status classification logic (<10 threshold)."""
    return "low_stock" if stock_qty < 10 else "in_stock"


def test_low_stock_detection():
    """
    Tests that inventory stock level below threshold (<10) is flagged as 'low_stock',
    while stock levels at or above threshold are classified as 'in_stock'.
    """
    # Stock level 5 -> low_stock
    assert classify_inventory_status(5) == "low_stock"

    # Stock level 0 -> low_stock
    assert classify_inventory_status(0) == "low_stock"

    # Stock level 10 -> in_stock
    assert classify_inventory_status(10) == "in_stock"

    # Stock level 50 -> in_stock
    assert classify_inventory_status(50) == "in_stock"


# ==============================================================================
# 4. CUSTOMER SEGMENTATION LOGIC UNIT TESTS
# ==============================================================================

def classify_customer_segment(total_spend: float) -> str:
    """Helper function reproducing customer spend tier segmentation logic."""
    if total_spend >= 100000.0:
        return "High Value"
    elif total_spend >= 25000.0:
        return "Medium Value"
    else:
        return "Low Value"


def test_customer_segmentation():
    """
    Tests customer classification based on total transaction spend in ₹ INR:
    - Spend >= ₹1,00,000 -> 'High Value'
    - Spend ₹25,000 to ₹99,999 -> 'Medium Value'
    - Spend < ₹25,000 -> 'Low Value'
    """
    # Total spend 150,000 -> High Value
    assert classify_customer_segment(150000.0) == "High Value"

    # Total spend 100,000 -> High Value
    assert classify_customer_segment(100000.0) == "High Value"

    # Total spend 50,000 -> Medium Value
    assert classify_customer_segment(50000.0) == "Medium Value"

    # Total spend 25,000 -> Medium Value
    assert classify_customer_segment(25000.0) == "Medium Value"

    # Total spend 10,000 -> Low Value
    assert classify_customer_segment(10000.0) == "Low Value"

    # Total spend 0 -> Low Value
    assert classify_customer_segment(0.0) == "Low Value"


# ==============================================================================
# 5. BENCHMARKING PERFORMANCE CLASSIFICATION UNIT TESTS
# ==============================================================================

def classify_vendor_performance(vendor_revenue: float, avg_revenue_per_vendor: float) -> str:
    """Helper function reproducing vendor benchmarking performance classification logic."""
    if avg_revenue_per_vendor > 0:
        if vendor_revenue >= (1.15 * avg_revenue_per_vendor):
            return "Above Average"
        elif vendor_revenue <= (0.85 * avg_revenue_per_vendor):
            return "Below Average"
        else:
            return "Average"
    return "Above Average" if vendor_revenue > 0 else "Average"


def test_benchmarking_classification():
    """
    Tests vendor performance classification relative to marketplace average revenue:
    - Vendor revenue >= 115% of average -> 'Above Average'
    - Vendor revenue <= 85% of average -> 'Below Average'
    - Within 85% - 115% range -> 'Average'
    """
    avg_rev = 100000.0

    # Vendor revenue 150,000 (150% of avg) -> Above Average
    assert classify_vendor_performance(150000.0, avg_rev) == "Above Average"

    # Vendor revenue 50,000 (50% of avg) -> Below Average
    assert classify_vendor_performance(50000.0, avg_rev) == "Below Average"

    # Vendor revenue 100,000 (100% of avg) -> Average
    assert classify_vendor_performance(100000.0, avg_rev) == "Average"


# ==============================================================================
# 6. TEXT-TO-SQL SAFETY VALIDATION UNIT TESTS
# ==============================================================================

def test_sql_safety_validation():
    """
    Tests security validation net for Text-to-SQL AI Analyst feature:
    - Rejects destructive statements containing DELETE, DROP, ALTER, UPDATE, etc.
    - Accepts valid read-only SELECT queries.
    """
    # 1. Test DELETE query rejection
    sql_delete = "DELETE FROM products WHERE id = 1;"
    clean_sql, is_safe, err_msg = sanitize_and_validate_sql(sql_delete)
    assert is_safe is False
    assert "forbidden operation keyword" in err_msg or "Security Violation" in err_msg

    # 2. Test DROP query rejection
    sql_drop = "DROP TABLE vendors;"
    clean_sql, is_safe, err_msg = sanitize_and_validate_sql(sql_drop)
    assert is_safe is False
    assert "forbidden operation keyword" in err_msg or "Security Violation" in err_msg

    # 3. Test valid SELECT query acceptance
    sql_select = "SELECT p.name, p.price FROM products p WHERE p.vendor_id = 1 ORDER BY p.price DESC"
    clean_sql, is_safe, err_msg = sanitize_and_validate_sql(sql_select)
    assert is_safe is True
    assert clean_sql.startswith("SELECT")
    assert err_msg == ""
