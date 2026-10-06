"""Pydantic schemas for the JSON API."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    product_id: str
    name: str
    category: str = "General"
    price: float = 0.0
    stock_qty: int = 0
    return_window_days: int = 7


class ProductIn(ProductBase):
    pass


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    stock_status: str | None = None


class OrderBase(BaseModel):
    order_id: str
    customer_name: str
    customer_email: str | None = None
    product_id: str | None = None
    order_date: datetime | None = None
    delivery_date: datetime | None = None
    delivery_status: str = "Pending"
    payment_status: str = "Paid"


class OrderIn(OrderBase):
    pass


class OrderOut(OrderBase):
    model_config = ConfigDict(from_attributes=True)
    days_since_delivery: int | None = None


class TicketBase(BaseModel):
    ticket_id: str
    order_id: str
    customer_claim: str | None = None
    proof_url: str | None = None
    agent_decision: str = "Pending"
    policy_checks: str | None = ""
    status: str = "In-Progress"


class TicketIn(TicketBase):
    pass


class TicketOut(TicketBase):
    model_config = ConfigDict(from_attributes=True)
    updated_at: datetime | None = None
