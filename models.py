from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base


class Vendor(Base):
    """
    Represents vendor profiles and platform admins in ShopSense.
    """
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="vendor")  # "admin" or "vendor"
    status = Column(String, nullable=False, default="pending")  # "active", "pending", "suspended"
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    products = relationship("Product", back_populates="vendor", cascade="all, delete-orphan")


class Product(Base):
    """
    Represents products listed by vendors.
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    category = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    stock_qty = Column(Integer, nullable=False, default=0)

    # Relationships
    vendor = relationship("Vendor", back_populates="products")
    transactions = relationship("Transaction", back_populates="product", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")


class Customer(Base):
    """
    Represents customers purchasing products on ShopSense.
    """
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)

    # Relationships
    transactions = relationship("Transaction", back_populates="customer")


class Transaction(Base):
    """
    Represents completed purchase transactions by customers.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    customer = relationship("Customer", back_populates="transactions")
    product = relationship("Product", back_populates="transactions")


class Review(Base):
    """
    Represents customer product reviews with rule-based sentiment scoring & extracted pros/cons (Milestone 2).
    """
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    customer_name = Column(String, nullable=False)
    review_text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)  # 1 to 5
    sentiment_score = Column(Float, nullable=False, default=0.0)  # -1.0 to +1.0
    sentiment_label = Column(String, nullable=False, default="Neutral")  # "Positive", "Neutral", "Negative"
    pros = Column(String, nullable=True)  # extracted pros
    cons = Column(String, nullable=True)  # extracted cons
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    product = relationship("Product", back_populates="reviews")


class ActivityLog(Base):
    """
    Represents live system activity events across ShopSense with UTC timezone support.
    """
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)  # "vendor_registered", "status_changed", "product_added", "sale_simulated", "review_added"
    description = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
