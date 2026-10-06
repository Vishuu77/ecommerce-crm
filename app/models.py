"""ORM models — products, orders, tickets, and the customer-storefront layer.

Storefront additions: User, OTP, CartItem, OrderItem, Payment, Notification.
"""
from datetime import datetime
from sqlalchemy import (Column, Integer, String, Float, DateTime, ForeignKey,
                        Text, Boolean, UniqueConstraint)
from sqlalchemy.orm import relationship

from app.database import Base


# ================================================================ catalog
class Product(Base):
    __tablename__ = "products"

    product_id = Column(String, primary_key=True)          # PROD-EAR-001
    name = Column(String, nullable=False)
    category = Column(String, default="General")
    price = Column(Float, default=0.0)                     # selling price
    mrp = Column(Float, default=0.0)                       # list price (strikethrough)
    rating = Column(Float, default=0.0)                    # 0..5
    review_count = Column(Integer, default=0)
    stock_qty = Column(Integer, default=0)
    return_window_days = Column(Integer, default=7)
    description = Column(Text, default="")
    image_url = Column(String, default="")
    active = Column(Boolean, default=True)

    orders = relationship("Order", back_populates="product")

    @property
    def stock_status(self) -> str:
        if self.stock_qty <= 0:
            return "Out of Stock"
        if self.stock_qty <= 10:
            return "Low Stock"
        return "In Stock"

    @property
    def discount_pct(self) -> int:
        """Percent off MRP, or 0 when there is no genuine markdown."""
        if self.mrp and self.mrp > self.price > 0:
            return round((self.mrp - self.price) / self.mrp * 100)
        return 0


# ================================================================ customers
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, default="")  # E.164, one account per number
    password_hash = Column(String, nullable=False)
    phone_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    cart_items = relationship("CartItem", back_populates="user",
                              cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user")

    @property
    def phone_last4(self) -> str:
        return self.phone[-4:] if self.phone else ""


class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String, index=True, nullable=False)
    code_hash = Column(String, nullable=False)
    purpose = Column(String, default="verify")             # verify | login
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0)
    consumed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ================================================================ cart
class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.product_id"), nullable=False)
    qty = Column(Integer, default=1)
    added_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="cart_items")
    product = relationship("Product")


# ================================================================ orders
class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True)            # ORD-98231
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String)
    customer_phone = Column(String, default="")
    shipping_address = Column(Text, default="")
    product_id = Column(String, ForeignKey("products.product_id"), nullable=True)
    order_date = Column(DateTime, default=datetime.utcnow)
    delivery_date = Column(DateTime, nullable=True)
    delivery_status = Column(String, default="Pending")    # Pending/Shipped/Delivered/Cancelled
    payment_status = Column(String, default="Pending")     # Pending/Paid/Refunded/Failed
    total_amount = Column(Float, default=0.0)

    product = relationship("Product", back_populates="orders")
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="order")

    @property
    def days_since_delivery(self) -> int | None:
        if not self.delivery_date:
            return None
        return (datetime.utcnow() - self.delivery_date).days


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, ForeignKey("orders.order_id"), nullable=False)
    product_id = Column(String, ForeignKey("products.product_id"), nullable=False)
    name = Column(String, default="")                      # snapshot at purchase
    unit_price = Column(Float, default=0.0)
    qty = Column(Integer, default=1)
    line_total = Column(Float, default=0.0)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, ForeignKey("orders.order_id"), nullable=False)
    provider = Column(String, default="razorpay")          # razorpay | simulate
    provider_order_id = Column(String, default="")
    provider_payment_id = Column(String, default="")
    amount = Column(Float, default=0.0)
    currency = Column(String, default="INR")
    status = Column(String, default="created")             # created/paid/failed/refunded
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = relationship("Order", back_populates="payments")


# ================================================================ tickets
class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(String, primary_key=True)           # TCK-501
    order_id = Column(String, ForeignKey("orders.order_id"))
    customer_claim = Column(Text)
    proof_url = Column(String, nullable=True)
    agent_decision = Column(String, default="Pending")
    policy_checks = Column(Text, default="")
    status = Column(String, default="In-Progress")         # In-Progress / Resolved / Escalated
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = relationship("Order", back_populates="tickets")


# ================================================================ notifications
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel = Column(String, default="whatsapp")           # whatsapp | sms | email | system
    to = Column(String, default="")
    kind = Column(String, default="")                      # otp | order | payment | status
    body = Column(Text, default="")
    status = Column(String, default="queued")              # queued/sent/failed/simulated
    error = Column(String, default="")
    order_id = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
