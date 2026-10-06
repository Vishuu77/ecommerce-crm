"""CRUD helpers."""
from datetime import datetime
from sqlalchemy.orm import Session
from app import models, schemas


# ---------------------------------------------------------------- products
def list_products(db: Session, q: str | None = None, category: str | None = None):
    query = db.query(models.Product)
    if q:
        like = f"%{q}%"
        query = query.filter((models.Product.name.ilike(like)) |
                             (models.Product.product_id.ilike(like)))
    if category:
        query = query.filter(models.Product.category == category)
    return query.order_by(models.Product.product_id).all()


def get_product(db: Session, product_id: str):
    return db.get(models.Product, product_id)


def create_product(db: Session, data: schemas.ProductIn):
    obj = models.Product(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_product(db: Session, product_id: str, data: schemas.ProductIn):
    obj = db.get(models.Product, product_id)
    if not obj:
        return None
    for k, v in data.model_dump(exclude={"product_id"}).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_product(db: Session, product_id: str) -> bool:
    obj = db.get(models.Product, product_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


# ---------------------------------------------------------------- orders
def list_orders(db: Session, status: str | None = None, q: str | None = None):
    query = db.query(models.Order)
    if status:
        query = query.filter(models.Order.delivery_status == status)
    if q:
        like = f"%{q}%"
        query = query.filter((models.Order.customer_name.ilike(like)) |
                             (models.Order.order_id.ilike(like)))
    return query.order_by(models.Order.order_date.desc()).all()


def get_order(db: Session, order_id: str):
    return db.get(models.Order, order_id)


def create_order(db: Session, data: schemas.OrderIn):
    payload = data.model_dump()
    payload["order_date"] = payload.get("order_date") or datetime.utcnow()
    obj = models.Order(**payload)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_order(db: Session, order_id: str, data: schemas.OrderIn):
    obj = db.get(models.Order, order_id)
    if not obj:
        return None
    for k, v in data.model_dump(exclude={"order_id"}).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_order(db: Session, order_id: str) -> bool:
    obj = db.get(models.Order, order_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


# ---------------------------------------------------------------- tickets
def list_tickets(db: Session, status: str | None = None):
    query = db.query(models.Ticket)
    if status:
        query = query.filter(models.Ticket.status == status)
    return query.order_by(models.Ticket.updated_at.desc()).all()


def get_ticket(db: Session, ticket_id: str):
    return db.get(models.Ticket, ticket_id)


def create_ticket(db: Session, data: schemas.TicketIn):
    obj = models.Ticket(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_ticket(db: Session, ticket_id: str, data: schemas.TicketIn):
    obj = db.get(models.Ticket, ticket_id)
    if not obj:
        return None
    for k, v in data.model_dump(exclude={"ticket_id"}).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def delete_ticket(db: Session, ticket_id: str) -> bool:
    obj = db.get(models.Ticket, ticket_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


# ---------------------------------------------------------------- dashboard
def dashboard_stats(db: Session) -> dict:
    products = db.query(models.Product).all()
    orders = db.query(models.Order).all()
    tickets = db.query(models.Ticket).all()
    revenue = sum(p.price for o in orders for p in [o.product] if p)
    return {
        "products": len(products),
        "orders": len(orders),
        "tickets": len(tickets),
        "open_tickets": sum(1 for t in tickets if t.status != "Resolved"),
        "low_stock": sum(1 for p in products if p.stock_qty <= 10),
        "revenue": round(revenue, 2),
        "delivered": sum(1 for o in orders if o.delivery_status == "Delivered"),
    }
