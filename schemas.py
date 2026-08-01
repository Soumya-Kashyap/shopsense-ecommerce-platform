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


# ==========================================
# ACTIVITY LOG SCHEMAS
# ==========================================

class ActivityLogResponse(BaseModel):
    id: int
    event_type: str
    description: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
