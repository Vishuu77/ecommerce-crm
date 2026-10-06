"""Seed sample data (products, users, orders, tickets)."""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models, auth

# (id, name, category, price, mrp, rating, reviews, stock, window, desc)
SAMPLE_PRODUCTS = [
    ("PROD-EAR-001", "AeroSound Pro Wireless Earbuds", "Electronics",
     2499.0, 4999.0, 4.4, 18342, 45, 7,
     "Bluetooth 5.3 earbuds, 30-hr battery, ENC mic"),
    ("PROD-SW-002", "PulseFit Smartwatch", "Electronics",
     3999.0, 6999.0, 4.2, 9271, 62, 7,
     '1.85" AMOLED, SpO2, heart rate, 7-day battery'),
    ("PROD-PB-003", "PowerMax 10000mAh Power Bank", "Electronics",
     999.0, 1799.0, 4.1, 12045, 8, 7,
     "22.5W fast charge, Type-C in/out, BIS certified"),
    ("PROD-KT-004", "Cotton Kurta Men's", "Fashion",
     799.0, 1499.0, 4.3, 5382, 96, 10,
     "Pure cotton straight kurta, sizes S-XXL"),
    ("PROD-CC-005", "FastCharge Type-C Cable 1.5m", "Electronics",
     249.0, 599.0, 4.5, 31208, 410, 7,
     "60W PD, nylon braided, 10,000-bend tested"),
    ("PROD-BK-006", "Python Made Simple (Paperback)", "Books",
     449.0, 699.0, 4.6, 2140, 85, 15,
     "Beginner-friendly Python, Indian edition"),
    ("PROD-HK-007", "Steel Masala Dabba", "Home & Kitchen",
     549.0, 999.0, 4.0, 1876, 6, 7,
     "Stainless steel 7-compartment spice box"),
    ("PROD-BT-008", "Copper Water Bottle 1L", "Home & Kitchen",
     649.0, 1299.0, 4.2, 4390, 130, 7,
     "Pure copper, lab-tested, leak-proof"),
    ("PROD-YM-009", "FitIndia Anti-skid Yoga Mat 6mm", "Sports & Fitness",
     699.0, 1199.0, 4.4, 7752, 88, 7,
     "6mm TPE, anti-skid, with carry strap"),
    ("PROD-FW-010", "Ayurveda Naturals Neem Face Wash", "Beauty",
     199.0, 349.0, 4.3, 15604, 310, 7,
     "150ml, neem + turmeric, for oily skin"),
]


def seed(db: Session):
    """Idempotent seeding — only fills what is empty."""
    if db.query(models.Product).count() == 0:
        for pid, name, cat, price, mrp, rating, reviews, stock, win, desc in SAMPLE_PRODUCTS:
            db.add(models.Product(product_id=pid, name=name, category=cat, price=price,
                                  mrp=mrp, rating=rating, review_count=reviews,
                                  stock_qty=stock, return_window_days=win,
                                  description=desc,
                                  image_url=f"/static/products/{pid}.svg"))

    # demo customer (password: demo1234) — dummy number, so the real owner can
    # still register their own phone (phone is unique)
    if db.query(models.User).count() == 0:
        db.add(models.User(name="Vishnu", email="vishnu@example.com",
                           phone="+919000000000",
                           password_hash=auth.hash_password("demo1234"),
                           phone_verified=True))

    if db.query(models.Order).count() == 0:
        now = datetime.utcnow()
        db.add(models.Order(
            order_id="ORD-98231", customer_name="Vishnu",
            customer_email="vishnu@example.com", customer_phone="+916361222162",
            product_id="PROD-EAR-001", order_date=now - timedelta(days=8),
            delivery_date=now - timedelta(days=3), delivery_status="Delivered",
            payment_status="Paid", total_amount=2499.0,
            shipping_address="12 MG Road, Bengaluru 560001"))
        db.add(models.Order(
            order_id="ORD-98232", customer_name="Priya",
            customer_email="priya@example.com", product_id="PROD-SW-002",
            order_date=now - timedelta(days=2), delivery_date=None,
            delivery_status="Shipped", payment_status="Paid", total_amount=3999.0))

    if db.query(models.Ticket).count() == 0:
        db.add(models.Ticket(
            ticket_id="TCK-501", order_id="ORD-98231",
            customer_claim="Received broken earbuds — left bud cracked on arrival",
            proof_url="uploads/vishnu_proof.jpg",
            agent_decision="Pending", policy_checks="", status="In-Progress"))
    db.commit()
