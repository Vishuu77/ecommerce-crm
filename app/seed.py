"""Seed sample data (roadmap: products, Vishnu's order, a ticket)."""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models

SAMPLE_PRODUCTS = [
    ("PROD-EAR-001", "AeroSound Pro Wireless Earbuds", "Electronics", 2499.0, 45, 7),
    ("PROD-SW-002", "PulseFit Smartwatch", "Electronics", 3999.0, 62, 7),
    ("PROD-PB-003", "PowerMax 10000mAh Power Bank", "Electronics", 999.0, 8, 7),
    ("PROD-KT-004", "Cotton Kurta Men's", "Fashion", 799.0, 96, 10),
    ("PROD-CC-005", "FastCharge Type-C Cable", "Electronics", 249.0, 410, 7),
    ("PROD-BK-006", "Python Made Simple (Paperback)", "Books", 449.0, 85, 15),
    ("PROD-HK-007", "Steel Masala Dabba", "Home & Kitchen", 549.0, 6, 7),
    ("PROD-BT-008", "Copper Water Bottle 1L", "Home & Kitchen", 649.0, 130, 7),
]


def seed(db: Session):
    """Idempotent seeding — only if empty."""
    if db.query(models.Product).count() == 0:
        for pid, name, cat, price, stock, win in SAMPLE_PRODUCTS:
            db.add(models.Product(product_id=pid, name=name, category=cat,
                                  price=price, stock_qty=stock, return_window_days=win))

    if db.query(models.Order).count() == 0:
        now = datetime.utcnow()
        db.add(models.Order(
            order_id="ORD-98231", customer_name="Vishnu",
            customer_email="vishnu@example.com", product_id="PROD-EAR-001",
            order_date=now - timedelta(days=8), delivery_date=now - timedelta(days=3),
            delivery_status="Delivered", payment_status="Paid"))
        db.add(models.Order(
            order_id="ORD-98232", customer_name="Priya",
            customer_email="priya@example.com", product_id="PROD-SW-002",
            order_date=now - timedelta(days=2), delivery_date=None,
            delivery_status="Shipped", payment_status="Paid"))

    if db.query(models.Ticket).count() == 0:
        db.add(models.Ticket(
            ticket_id="TCK-501", order_id="ORD-98231",
            customer_claim="Received broken earbuds — left bud cracked on arrival",
            proof_url="uploads/vishnu_proof.jpg",
            agent_decision="Pending", policy_checks="",
            status="In-Progress"))
    db.commit()
