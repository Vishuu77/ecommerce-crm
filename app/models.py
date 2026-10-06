"""ORM models — Products, Orders, Tickets (roadmap schema)."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    product_id = Column(String, primary_key=True)          # PROD-EAR-001
    name = Column(String, nullable=False)
    category = Column(String, default="General")
    price = Column(Float, default=0.0)
    stock_qty = Column(Integer, default=0)
    return_window_days = Column(Integer, default=7)

    orders = relationship("Order", back_populates="product")

    @property
    def stock_status(self) -> str:
        if self.stock_qty <= 0:
            return "Out of Stock"
        if self.stock_qty <= 10:
            return "Low Stock"
        return "In Stock"


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True)            # ORD-98231
    customer_name = Column(String, nullable=False)
    customer_email = Column(String)
    product_id = Column(String, ForeignKey("products.product_id"))
    order_date = Column(DateTime, default=datetime.utcnow)
    delivery_date = Column(DateTime, nullable=True)
    delivery_status = Column(String, default="Pending")    # Pending / Shipped / Delivered
    payment_status = Column(String, default="Paid")        # Paid / Refunded

    product = relationship("Product", back_populates="orders")
    tickets = relationship("Ticket", back_populates="order")

    @property
    def days_since_delivery(self) -> int | None:
        if not self.delivery_date:
            return None
        return (datetime.utcnow() - self.delivery_date).days


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
