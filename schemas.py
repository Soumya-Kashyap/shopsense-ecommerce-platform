from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ==========================================
# AUTH & LOGIN SCHEMAS
# ==========================================

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered user or vendor email address", json_schema_extra={"example": "admin@shopsense.com"})
    password: str = Field(..., description="Account password", json_schema_extra={"example": "admin"})


class LoginResponse(BaseModel):
    access_token: str = Field(..., description="Session authorization token for API access", json_schema_extra={"example": "dummy-token-admin-1"})
    token_type: str = Field("bearer", description="HTTP authorization header scheme", json_schema_extra={"example": "bearer"})
    role: str = Field(..., description="User role classification ('admin' or 'vendor')", json_schema_extra={"example": "admin"})
    status: str = Field(..., description="Account status ('active', 'pending', or 'suspended')", json_schema_extra={"example": "active"})
    vendor_id: int = Field(..., description="Unique database ID of the logged-in user or vendor", json_schema_extra={"example": 1})
    name: str = Field(..., description="Full display name of the user", json_schema_extra={"example": "ShopSense Administrator"})
    email: str = Field(..., description="Registered email address", json_schema_extra={"example": "admin@shopsense.com"})


# ==========================================
# VENDOR SCHEMAS
# ==========================================

class VendorBase(BaseModel):
    name: str = Field(..., min_length=1, description="Vendor company or brand name", json_schema_extra={"example": "Sony India"})
    email: EmailStr = Field(..., description="Valid business contact email address", json_schema_extra={"example": "contact@sony.com"})
    phone: str | None = Field(None, description="Optional vendor contact phone number", json_schema_extra={"example": "+91-9876543210"})


class VendorCreate(VendorBase):
    password: str = Field(..., min_length=6, description="Account password (must be at least 6 characters)", json_schema_extra={"example": "vendor123"})


class VendorUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, description="Updated vendor brand name", json_schema_extra={"example": "Sony India Pvt Ltd"})
    email: EmailStr | None = Field(None, description="Updated email address", json_schema_extra={"example": "support@sony.com"})
    phone: str | None = Field(None, description="Updated contact phone number", json_schema_extra={"example": "+91-9876543211"})


class VendorStatusUpdate(BaseModel):
    status: Literal["active", "pending", "suspended"] = Field(..., description="New vendor approval status ('active', 'pending', 'suspended')", json_schema_extra={"example": "active"})


class VendorResponse(VendorBase):
    id: int = Field(..., description="Unique vendor ID", json_schema_extra={"example": 1})
    role: str = Field(..., description="User role ('vendor')", json_schema_extra={"example": "vendor"})
    status: str = Field(..., description="Account status ('active', 'pending', 'suspended')", json_schema_extra={"example": "active"})
    created_at: datetime = Field(..., description="Vendor registration timestamp")

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# VENDOR ANALYTICS SCHEMAS
# ==========================================

class VendorSalesSummary(BaseModel):
    vendor_id: int = Field(..., description="Vendor unique identifier", json_schema_extra={"example": 1})
    vendor_name: str = Field(..., description="Vendor company or brand name", json_schema_extra={"example": "Samsung"})
    total_orders: int = Field(..., description="Total completed order count", json_schema_extra={"example": 18})
    total_units_sold: int = Field(..., description="Total quantity of units sold across all products", json_schema_extra={"example": 35})
    total_revenue: float = Field(..., description="Gross revenue generated in Indian Rupees (₹ INR)", json_schema_extra={"example": 388996.00})


# ==========================================
# PRODUCT SCHEMAS
# ==========================================

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, description="Product title", json_schema_extra={"example": "Galaxy S24 Ultra 5G"})
    price: float = Field(..., gt=0, description="Product unit price in ₹ INR (must be > 0)", json_schema_extra={"example": 129999.00})
    stock_qty: int = Field(..., ge=0, description="Current stock inventory count (must be >= 0)", json_schema_extra={"example": 25})
    description: str | None = Field(None, description="Detailed product description", json_schema_extra={"example": "Flagship smartphone with Snapdragon 8 Gen 3 and AI features."})
    image_url: str | None = Field(None, description="Product image URL or Base64 thumbnail string")
    category: str | None = Field(None, description="Product classification category", json_schema_extra={"example": "Smartphones & Mobile Devices"})
    tags: str | None = Field(None, description="Comma-separated SEO keyword tags", json_schema_extra={"example": "smartphone, 5g, flagship, samsung"})


class ProductCreate(ProductBase):
    vendor_id: int = Field(..., description="ID of the vendor listing this product", json_schema_extra={"example": 1})


class ProductResponse(ProductBase):
    id: int = Field(..., description="Unique product database ID", json_schema_extra={"example": 1})
    vendor_id: int = Field(..., description="Vendor owner database ID", json_schema_extra={"example": 1})

    model_config = ConfigDict(from_attributes=True)


class RestockRequest(BaseModel):
    quantity: int = Field(..., gt=0, description="Quantity of units to add to current inventory", json_schema_extra={"example": 20})


class RestockResponse(BaseModel):
    product_id: int = Field(..., description="Unique product database ID", json_schema_extra={"example": 4})
    product_name: str = Field(..., description="Name of the restocked product", json_schema_extra={"example": "Flip 6 Waterproof Speaker"})
    quantity_added: int = Field(..., description="Quantity added in this restock request", json_schema_extra={"example": 20})
    new_stock_qty: int = Field(..., description="Updated total inventory stock quantity", json_schema_extra={"example": 25})
    message: str = Field(..., description="Confirmation message describing the restock event")


# ==========================================
# INVENTORY SCHEMAS
# ==========================================

class InventoryItemResponse(BaseModel):
    product_id: int = Field(..., description="Product unique identifier", json_schema_extra={"example": 4})
    product_name: str = Field(..., description="Product title", json_schema_extra={"example": "Flip 6 Waterproof Speaker"})
    vendor_id: int = Field(..., description="Owner vendor ID", json_schema_extra={"example": 3})
    vendor_name: str = Field(..., description="Owner vendor brand name", json_schema_extra={"example": "JBL Electronics"})
    stock_qty: int = Field(..., description="Current stock inventory count", json_schema_extra={"example": 5})
    price: float = Field(..., description="Unit price in ₹ INR", json_schema_extra={"example": 9999.00})
    status: str = Field(..., description="Inventory status flag ('low_stock' if stock_qty < 10, else 'in_stock')", json_schema_extra={"example": "low_stock"})

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# CUSTOMER SEGMENTATION SCHEMAS
# ==========================================

class CustomerSegmentResponse(BaseModel):
    customer_id: int = Field(..., description="Customer unique database ID", json_schema_extra={"example": 1})
    customer_name: str = Field(..., description="Customer full name", json_schema_extra={"example": "Rahul Sharma"})
    email: str = Field(..., description="Customer email address", json_schema_extra={"example": "rahul.sharma@gmail.com"})
    total_spend: float = Field(..., description="Total aggregate spend across all orders in ₹ INR", json_schema_extra={"example": 130996.00})
    total_orders: int = Field(..., description="Total completed transaction count", json_schema_extra={"example": 4})
    segment: str = Field(..., description="Tier segment classification ('High Value' >= 100k, 'Medium Value' 25k-100k, 'Low Value' < 25k)", json_schema_extra={"example": "High Value"})

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# TOP SELLING PRODUCT RECOMMENDATION SCHEMAS
# ==========================================

class TopSellingProductResponse(BaseModel):
    product_id: int = Field(..., description="Product database ID", json_schema_extra={"example": 1})
    product_name: str = Field(..., description="Product title", json_schema_extra={"example": "Galaxy Buds Pro Wireless Earbuds"})
    vendor_id: int = Field(..., description="Vendor owner ID", json_schema_extra={"example": 1})
    vendor_name: str = Field(..., description="Vendor brand name", json_schema_extra={"example": "Samsung"})
    category: str | None = Field(None, description="Vision category classification", json_schema_extra={"example": "Audio & Headphones"})
    price: float = Field(..., description="Unit price in ₹ INR", json_schema_extra={"example": 12999.00})
    units_sold: int = Field(..., description="Total quantity of units sold across all completed orders", json_schema_extra={"example": 12})
    total_revenue: float = Field(..., description="Total revenue generated by this product in ₹ INR", json_schema_extra={"example": 155988.00})

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# CUSTOMER REVIEW & SENTIMENT SCHEMAS
# ==========================================

class ReviewCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, description="Customer reviewer full name", json_schema_extra={"example": "Ananya Roy"})
    review_text: str = Field(..., min_length=2, description="Customer text review content", json_schema_extra={"example": "Fantastic sound quality and incredible noise cancellation!"})
    rating: int = Field(..., ge=1, le=5, description="Star rating between 1 and 5", json_schema_extra={"example": 5})


class ReviewResponse(BaseModel):
    id: int = Field(..., description="Review unique ID", json_schema_extra={"example": 1})
    product_id: int = Field(..., description="Associated product database ID", json_schema_extra={"example": 1})
    customer_name: str = Field(..., description="Reviewer full name", json_schema_extra={"example": "Ananya Roy"})
    review_text: str = Field(..., description="Review text content")
    rating: int = Field(..., description="Star rating (1 to 5)", json_schema_extra={"example": 5})
    sentiment_score: float = Field(..., description="Calculated sentiment score (-1.0 to +1.0)", json_schema_extra={"example": 0.95})
    sentiment_label: str = Field(..., description="Sentiment classification ('Positive', 'Neutral', or 'Negative')", json_schema_extra={"example": "Positive"})
    pros: str | None = Field(None, description="Extracted positive feature highlights")
    cons: str | None = Field(None, description="Extracted negative feature drawbacks")
    created_at: datetime = Field(..., description="Review creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class ReviewAggregateSummary(BaseModel):
    total_reviews: int = Field(..., description="Total number of reviews for this product", json_schema_extra={"example": 8})
    average_rating: float = Field(..., description="Average star rating (1.0 to 5.0)", json_schema_extra={"example": 4.75})
    positive_percentage: float = Field(..., description="Percentage of positive reviews (0.0 to 100.0%)", json_schema_extra={"example": 87.5})
    neutral_percentage: float = Field(..., description="Percentage of neutral reviews (0.0 to 100.0%)", json_schema_extra={"example": 12.5})
    negative_percentage: float = Field(..., description="Percentage of negative reviews (0.0 to 100.0%)", json_schema_extra={"example": 0.0})
    top_pros: list[str] = Field(default_factory=list, description="List of most frequently mentioned pros")
    top_cons: list[str] = Field(default_factory=list, description="List of most frequently mentioned cons")


class ProductReviewsResponse(BaseModel):
    product_id: int = Field(..., description="Target product database ID", json_schema_extra={"example": 1})
    reviews: list[ReviewResponse] = Field(default_factory=list, description="List of individual review objects")
    aggregate: ReviewAggregateSummary = Field(..., description="Aggregated rating & sentiment statistical metrics")


# ==========================================
# SALES TREND ANALYTICS SCHEMAS
# ==========================================

class SalesTrendDayItem(BaseModel):
    date: str = Field(..., description="Calendar date string YYYY-MM-DD", json_schema_extra={"example": "2026-09-11"})
    day_label: str = Field(..., description="Short weekday name e.g. Mon, Tue, Fri", json_schema_extra={"example": "Fri"})
    revenue: float = Field(..., description="Total revenue generated on this day in ₹ INR", json_schema_extra={"example": 190992.00})
    orders: int = Field(..., description="Total completed transaction count on this day", json_schema_extra={"example": 6})


# ==========================================
# CHART-READY ANALYTICS SCHEMAS
# ==========================================

class ChartItemResponse(BaseModel):
    label: str = Field(..., description="Category label for chart axes or legends", json_schema_extra={"example": "Samsung"})
    value: float = Field(..., description="Numeric value e.g. total revenue, order count, or share", json_schema_extra={"example": 388996.00})
    color: str | None = Field(None, description="Optional hex code or color string for visualization rendering", json_schema_extra={"example": "#34d399"})


# ==========================================
# BENCHMARKING SCHEMAS
# ==========================================

class MarketplaceAverages(BaseModel):
    avg_revenue_per_vendor: float = Field(..., description="Marketplace average revenue per vendor in ₹ INR", json_schema_extra={"example": 278325.00})
    avg_order_value: float = Field(..., description="Marketplace Average Order Value (AOV = total_revenue / total_orders)", json_schema_extra={"example": 36303.26})
    avg_units_per_vendor: float = Field(..., description="Marketplace average units sold per vendor", json_schema_extra={"example": 23.33})


class VendorBenchmarkItem(BaseModel):
    vendor_id: int = Field(..., description="Vendor unique database ID", json_schema_extra={"example": 1})
    vendor_name: str = Field(..., description="Vendor brand name", json_schema_extra={"example": "Samsung"})
    email: str = Field(..., description="Vendor email address", json_schema_extra={"example": "contact@samsung.com"})
    revenue: float = Field(..., description="Vendor total revenue in ₹ INR", json_schema_extra={"example": 388996.00})
    orders: int = Field(..., description="Vendor total completed orders", json_schema_extra={"example": 18})
    aov: float = Field(..., description="Vendor Average Order Value in ₹ INR", json_schema_extra={"example": 21610.89})
    units_sold: int = Field(..., description="Vendor total units sold", json_schema_extra={"example": 35})
    performance: Literal["Above Average", "Average", "Below Average"] = Field(..., description="Relative benchmark classification vs platform average", json_schema_extra={"example": "Above Average"})


class VendorBenchmarkResponse(BaseModel):
    marketplace_averages: MarketplaceAverages = Field(..., description="Platform-wide baseline metric averages")
    vendors: list[VendorBenchmarkItem] = Field(default_factory=list, description="Per-vendor benchmark performance metrics")


# ==========================================
# RAG AI SHOPPING ASSISTANT SCHEMAS
# ==========================================

class AssistantQuestionRequest(BaseModel):
    question: str = Field(..., min_length=2, description="Natural language customer shopping query", json_schema_extra={"example": "What are the best wireless earbuds under 15000?"})


class AssistantAnswerResponse(BaseModel):
    answer: str = Field(..., description="LLM-generated or context-based recommendation text response")
    matched_products: list[TopSellingProductResponse] = Field(default_factory=list, description="List of matching real products retrieved from database")
    fallback_used: bool = Field(False, description="Flag indicating if fallback catalog recommendation was used")


# ==========================================
# AI DATA ANALYST TEXT-TO-SQL SCHEMAS
# ==========================================

class AIAnalystRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Natural language vendor query regarding sales data", json_schema_extra={"example": "What is my top selling product by units sold?"})


class AIAnalystResponse(BaseModel):
    answer: str = Field(..., description="Natural language business summary synthesizing query findings")
    sql_query: str = Field(..., description="LLM-generated and safety-validated read-only SQL query string")
    data: list[dict[str, Any]] = Field(default_factory=list, description="Tabular rows returned by SQL query execution")
    query_success: bool = Field(True, description="Flag indicating if SQL query execution succeeded")


# ==========================================
# ACTIVITY LOG SCHEMAS
# ==========================================

class ActivityLogResponse(BaseModel):
    id: int = Field(..., description="Log entry database ID", json_schema_extra={"example": 1})
    event_type: str = Field(..., description="System event category e.g. VENDOR_APPROVAL, SALE_RECORDED", json_schema_extra={"example": "SALE_RECORDED"})
    description: str = Field(..., description="Human-readable log description message", json_schema_extra={"example": "Samsung recorded sale for product 'Galaxy Buds Pro Wireless Earbuds'"})
    timestamp: datetime = Field(..., description="Event timestamp")

    model_config = ConfigDict(from_attributes=True)
