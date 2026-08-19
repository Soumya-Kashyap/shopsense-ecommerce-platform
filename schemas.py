from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ==========================================
# AUTH & LOGIN SCHEMAS
# ==========================================

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class LoginResponse(BaseModel):
    access_token: str = Field(..., description="Session authentication token")
    token_type: str = Field("bearer", description="Token authorization type")
    role: str = Field(..., description="User role: 'admin' or 'vendor'")
    status: str = Field(..., description="Vendor status: 'active', 'pending', or 'suspended'")
    vendor_id: int = Field(..., description="Vendor / User ID")
    name: str = Field(..., description="User full name")
    email: str = Field(..., description="User email address")


# ==========================================
# VENDOR SCHEMAS
# ==========================================

class VendorBase(BaseModel):
    name: str = Field(..., min_length=1, description="Vendor full name or company name")
    email: EmailStr = Field(..., description="Valid email address")
    phone: Optional[str] = Field(None, description="Vendor contact phone number")


class VendorCreate(VendorBase):
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")


class VendorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class VendorStatusUpdate(BaseModel):
    status: Literal["active", "pending", "suspended"] = Field(..., description="New vendor status")


class VendorResponse(VendorBase):
    id: int
    role: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# VENDOR ANALYTICS SCHEMAS
# ==========================================

class VendorSalesSummary(BaseModel):
    vendor_id: int
    vendor_name: str
    total_orders: int = Field(..., description="Total number of transaction records")
    total_units_sold: int = Field(..., description="Total quantity of products sold")
    total_revenue: float = Field(..., description="Total revenue generated in currency (₹ INR)")


# ==========================================
# PRODUCT SCHEMAS
# ==========================================

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0, description="Product price must be greater than 0")
    stock_qty: int = Field(..., ge=0, description="Stock quantity cannot be negative")
    description: Optional[str] = Field(None, description="Product description")
    image_url: Optional[str] = Field(None, description="Base64 encoded image or thumbnail URL")
    category: Optional[str] = Field(None, description="Product category vision classification")
    tags: Optional[str] = Field(None, description="Comma-separated SEO tags")


class ProductCreate(ProductBase):
    vendor_id: int


class ProductResponse(ProductBase):
    id: int
    vendor_id: int

    model_config = ConfigDict(from_attributes=True)


class RestockRequest(BaseModel):
    quantity: int = Field(..., gt=0, description="Quantity of inventory to add")


class RestockResponse(BaseModel):
    product_id: int
    product_name: str
    quantity_added: int
    new_stock_qty: int
    message: str


# ==========================================
# INVENTORY SCHEMAS (MILESTONE 2)
# ==========================================

class InventoryItemResponse(BaseModel):
    product_id: int
    product_name: str
    vendor_id: int
    vendor_name: str
    stock_qty: int
    price: float
    status: str = Field(..., description="Inventory status: 'low_stock' if stock_qty < 10, else 'in_stock'")

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# CUSTOMER SEGMENTATION SCHEMAS (MILESTONE 2)
# ==========================================

class CustomerSegmentResponse(BaseModel):
    customer_id: int
    customer_name: str
    email: str
    total_spend: float = Field(..., description="Total spend across all transactions in ₹ INR")
    total_orders: int = Field(..., description="Total number of transactions completed")
    segment: str = Field(..., description="'High Value' (>=100000), 'Medium Value' (25000-99999), or 'Low Value' (<25000)")

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# TOP SELLING PRODUCT RECOMMENDATION SCHEMAS (MILESTONE 2)
# ==========================================

class TopSellingProductResponse(BaseModel):
    product_id: int
    product_name: str
    vendor_id: int
    vendor_name: str
    category: Optional[str] = None
    price: float
    units_sold: int = Field(..., description="Total units sold across completed transactions")
    total_revenue: float = Field(..., description="Total gross revenue generated by this product in ₹ INR")

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# CUSTOMER REVIEW & SENTIMENT SCHEMAS (MILESTONE 2)
# ==========================================

class ReviewCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, description="Customer reviewer name")
    review_text: str = Field(..., min_length=2, description="Customer review text content")
    rating: int = Field(..., ge=1, le=5, description="Star rating between 1 and 5")


class ReviewResponse(BaseModel):
    id: int
    product_id: int
    customer_name: str
    review_text: str
    rating: int
    sentiment_score: float = Field(..., description="Calculated sentiment score between -1.0 and +1.0")
    sentiment_label: str = Field(..., description="'Positive', 'Neutral', or 'Negative'")
    pros: Optional[str] = Field(None, description="Extracted positive key features/pros")
    cons: Optional[str] = Field(None, description="Extracted negative drawbacks/cons")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewAggregateSummary(BaseModel):
    total_reviews: int
    average_rating: float
    positive_percentage: float
    neutral_percentage: float
    negative_percentage: float
    top_pros: list[str]
    top_cons: list[str]


class ProductReviewsResponse(BaseModel):
    product_id: int
    reviews: list[ReviewResponse]
    aggregate: ReviewAggregateSummary


# ==========================================
# SALES TREND ANALYTICS SCHEMAS (MILESTONE 2)
# ==========================================

class SalesTrendDayItem(BaseModel):
    date: str = Field(..., description="Date string YYYY-MM-DD")
    day_label: str = Field(..., description="Day label e.g. Mon, Tue")
    revenue: float = Field(..., description="Total revenue generated on this day in ₹ INR")
    orders: int = Field(..., description="Total orders completed on this day")


# ==========================================
# ACTIVITY LOG SCHEMAS
# ==========================================

class ActivityLogResponse(BaseModel):
    id: int
    event_type: str
    description: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
