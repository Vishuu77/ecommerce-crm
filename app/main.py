"""E-commerce CRM — FastAPI app: JSON API + server-rendered admin UI.

Run locally:   uvicorn app.main:app --reload
Docs:          http://127.0.0.1:8000/docs
Admin UI:      http://127.0.0.1:8000/
"""
import os
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db, init_db, SessionLocal
from app import crud, schemas, models, seed, policy

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOADS = os.path.join(BASE, "uploads")
os.makedirs(UPLOADS, exist_ok=True)

app = FastAPI(title="E-commerce CRM", version="1.0.0",
              description="Products, Orders, and Returns/Tickets — local-first, cloud-ready.")

app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS), name="uploads")
templates = Jinja2Templates(directory=os.path.join(BASE, "templates"))


@app.on_event("startup")
def _startup():
    init_db()
    db = SessionLocal()
    try:
        seed.seed(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# ============================================================ JSON API
@app.get("/api/stats")
def api_stats(db: Session = Depends(get_db)):
    return crud.dashboard_stats(db)


@app.get("/api/products", response_model=list[schemas.ProductOut])
def api_products(q: str | None = None, category: str | None = None,
                 db: Session = Depends(get_db)):
    return crud.list_products(db, q, category)


@app.post("/api/products", response_model=schemas.ProductOut, status_code=201)
def api_create_product(data: schemas.ProductIn, db: Session = Depends(get_db)):
    if crud.get_product(db, data.product_id):
        raise HTTPException(409, "product_id already exists")
    return crud.create_product(db, data)


@app.get("/api/products/{product_id}", response_model=schemas.ProductOut)
def api_get_product(product_id: str, db: Session = Depends(get_db)):
    obj = crud.get_product(db, product_id)
    if not obj:
        raise HTTPException(404, "product not found")
    return obj


@app.put("/api/products/{product_id}", response_model=schemas.ProductOut)
def api_update_product(product_id: str, data: schemas.ProductIn, db: Session = Depends(get_db)):
    obj = crud.update_product(db, product_id, data)
    if not obj:
        raise HTTPException(404, "product not found")
    return obj


@app.delete("/api/products/{product_id}", status_code=204)
def api_delete_product(product_id: str, db: Session = Depends(get_db)):
    if not crud.delete_product(db, product_id):
        raise HTTPException(404, "product not found")


@app.get("/api/orders", response_model=list[schemas.OrderOut])
def api_orders(status: str | None = None, q: str | None = None, db: Session = Depends(get_db)):
    return crud.list_orders(db, status, q)


@app.post("/api/orders", response_model=schemas.OrderOut, status_code=201)
def api_create_order(data: schemas.OrderIn, db: Session = Depends(get_db)):
    if crud.get_order(db, data.order_id):
        raise HTTPException(409, "order_id already exists")
    return crud.create_order(db, data)


@app.get("/api/orders/{order_id}", response_model=schemas.OrderOut)
def api_get_order(order_id: str, db: Session = Depends(get_db)):
    obj = crud.get_order(db, order_id)
    if not obj:
        raise HTTPException(404, "order not found")
    return obj


@app.put("/api/orders/{order_id}", response_model=schemas.OrderOut)
def api_update_order(order_id: str, data: schemas.OrderIn, db: Session = Depends(get_db)):
    obj = crud.update_order(db, order_id, data)
    if not obj:
        raise HTTPException(404, "order not found")
    return obj


@app.delete("/api/orders/{order_id}", status_code=204)
def api_delete_order(order_id: str, db: Session = Depends(get_db)):
    if not crud.delete_order(db, order_id):
        raise HTTPException(404, "order not found")


@app.get("/api/tickets", response_model=list[schemas.TicketOut])
def api_tickets(status: str | None = None, db: Session = Depends(get_db)):
    return crud.list_tickets(db, status)


@app.post("/api/tickets", response_model=schemas.TicketOut, status_code=201)
def api_create_ticket(data: schemas.TicketIn, db: Session = Depends(get_db)):
    if crud.get_ticket(db, data.ticket_id):
        raise HTTPException(409, "ticket_id already exists")
    if not crud.get_order(db, data.order_id):
        raise HTTPException(400, "order_id does not exist")
    return crud.create_ticket(db, data)


@app.get("/api/tickets/{ticket_id}", response_model=schemas.TicketOut)
def api_get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    obj = crud.get_ticket(db, ticket_id)
    if not obj:
        raise HTTPException(404, "ticket not found")
    return obj


@app.put("/api/tickets/{ticket_id}", response_model=schemas.TicketOut)
def api_update_ticket(ticket_id: str, data: schemas.TicketIn, db: Session = Depends(get_db)):
    obj = crud.update_ticket(db, ticket_id, data)
    if not obj:
        raise HTTPException(404, "ticket not found")
    return obj


@app.delete("/api/tickets/{ticket_id}", status_code=204)
def api_delete_ticket(ticket_id: str, db: Session = Depends(get_db)):
    if not crud.delete_ticket(db, ticket_id):
        raise HTTPException(404, "ticket not found")


# ============================================================ Admin UI
@app.get("/", response_class=HTMLResponse)
def ui_dashboard(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "dashboard.html", {
        "stats": crud.dashboard_stats(db),
        "orders": crud.list_orders(db)[:5], "tickets": crud.list_tickets(db)[:5]})


@app.get("/ui/products", response_class=HTMLResponse)
def ui_products(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "products.html", {
        "products": crud.list_products(db, q), "q": q or ""})


@app.post("/ui/products")
def ui_create_product(product_id: str = Form(...), name: str = Form(...),
                      category: str = Form("General"), price: float = Form(0.0),
                      stock_qty: int = Form(0), return_window_days: int = Form(7),
                      db: Session = Depends(get_db)):
    if not crud.get_product(db, product_id):
        crud.create_product(db, schemas.ProductIn(
            product_id=product_id, name=name, category=category, price=price,
            stock_qty=stock_qty, return_window_days=return_window_days))
    return RedirectResponse("/ui/products", status_code=303)


@app.post("/ui/products/{product_id}/delete")
def ui_delete_product(product_id: str, db: Session = Depends(get_db)):
    crud.delete_product(db, product_id)
    return RedirectResponse("/ui/products", status_code=303)


@app.get("/ui/orders", response_class=HTMLResponse)
def ui_orders(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "orders.html", {
        "orders": crud.list_orders(db, q=q), "q": q or "",
        "products": crud.list_products(db)})


@app.post("/ui/orders")
def ui_create_order(order_id: str = Form(...), customer_name: str = Form(...),
                    customer_email: str = Form(""), product_id: str = Form(""),
                    delivery_status: str = Form("Pending"), payment_status: str = Form("Paid"),
                    db: Session = Depends(get_db)):
    if not crud.get_order(db, order_id):
        crud.create_order(db, schemas.OrderIn(
            order_id=order_id, customer_name=customer_name, customer_email=customer_email,
            product_id=product_id or None, delivery_status=delivery_status,
            payment_status=payment_status, order_date=datetime.utcnow()))
    return RedirectResponse("/ui/orders", status_code=303)


@app.post("/ui/orders/{order_id}/deliver")
def ui_mark_delivered(order_id: str, db: Session = Depends(get_db)):
    o = crud.get_order(db, order_id)
    if o:
        o.delivery_status = "Delivered"
        o.delivery_date = datetime.utcnow()
        db.commit()
    return RedirectResponse("/ui/orders", status_code=303)


@app.get("/ui/tickets", response_class=HTMLResponse)
def ui_tickets(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "tickets.html", {
        "tickets": crud.list_tickets(db),
        "orders": crud.list_orders(db)})


@app.post("/ui/tickets")
async def ui_create_ticket(order_id: str = Form(...), customer_claim: str = Form(...),
                           proof: UploadFile | None = File(None),
                           db: Session = Depends(get_db)):
    proof_url = None
    if proof is not None and proof.filename:
        safe = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{os.path.basename(proof.filename)}"
        with open(os.path.join(UPLOADS, safe), "wb") as f:
            f.write(await proof.read())
        proof_url = f"/uploads/{safe}"
    n = db.query(models.Ticket).count() + 501
    tid = f"TCK-{n}"
    while crud.get_ticket(db, tid):
        n += 1
        tid = f"TCK-{n}"
    crud.create_ticket(db, schemas.TicketIn(
        ticket_id=tid, order_id=order_id, customer_claim=customer_claim,
        proof_url=proof_url, agent_decision="Pending", policy_checks="",
        status="In-Progress"))
    return RedirectResponse("/ui/tickets", status_code=303)


@app.post("/ui/tickets/{ticket_id}/status")
def ui_ticket_status(ticket_id: str, status: str = Form(...), db: Session = Depends(get_db)):
    t = crud.get_ticket(db, ticket_id)
    if t:
        t.status = status
        t.updated_at = datetime.utcnow()
        db.commit()
    return RedirectResponse("/ui/tickets", status_code=303)


# ============================================================ CUSTOMER PORTAL
def _render(request, name, **ctx):
    return templates.TemplateResponse(request, name, ctx)


@app.get("/portal", response_class=HTMLResponse)
def portal_home(request: Request):
    return _render(request, "portal_home.html")


@app.get("/portal/order", response_class=HTMLResponse)
def portal_order(request: Request, order_id: str | None = None,
                 db: Session = Depends(get_db)):
    """Customer looks up their order by Order ID (roadmap: real-time input)."""
    order = crud.get_order(db, order_id) if order_id else None
    product = crud.get_product(db, order.product_id) if order and order.product_id else None
    tickets = db.query(models.Ticket).filter(models.Ticket.order_id == order_id).all() if order else []
    return _render(request, "portal_order.html", order=order, product=product,
                   order_id=order_id or "", tickets=tickets,
                   found=bool(order_id), claim_types=policy.CLAIM_TYPES)


@app.post("/portal/order/request", response_class=HTMLResponse)
async def portal_request(request: Request, order_id: str = Form(...),
                         claim_type: str = Form("damaged"),
                         customer_claim: str = Form(""),
                         proof: UploadFile | None = File(None),
                         db: Session = Depends(get_db)):
    """Raise a return/replacement request; runs the policy engine."""
    order = crud.get_order(db, order_id)
    product = crud.get_product(db, order.product_id) if order and order.product_id else None

    proof_url = None
    if proof is not None and proof.filename:
        safe = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{os.path.basename(proof.filename)}"
        with open(os.path.join(UPLOADS, safe), "wb") as f:
            f.write(await proof.read())
        proof_url = f"/uploads/{safe}"

    result = policy.check_policy(order, claim_type, bool(proof_url), product)

    ticket = None
    if order is not None and result.status in ("ELIGIBLE", "NEEDS_PROOF"):
        n = db.query(models.Ticket).count() + 501
        tid = f"TCK-{n}"
        while crud.get_ticket(db, tid):
            n += 1
            tid = f"TCK-{n}"
        decision = {"ELIGIBLE": f"{result.remedy} Approved", "NEEDS_PROOF": "Pending proof",
                    "NOT_ELIGIBLE": "Rejected"}[result.status]
        ticket = crud.create_ticket(db, schemas.TicketIn(
            ticket_id=tid, order_id=order_id,
            customer_claim=f"[{claim_type}] {customer_claim}".strip(),
            proof_url=proof_url, agent_decision=decision,
            policy_checks=result.summary,
            status="Resolved" if result.status == "ELIGIBLE" else "In-Progress"))

    return _render(request, "portal_result.html", order=order, product=product,
                   result=result, ticket=ticket, claim_type=claim_type)


@app.get("/portal/track", response_class=HTMLResponse)
def portal_track(request: Request, order_id: str | None = None, db: Session = Depends(get_db)):
    """Track a request by Order ID."""
    order = crud.get_order(db, order_id) if order_id else None
    tickets = db.query(models.Ticket).filter(models.Ticket.order_id == order_id).all() if order else []
    return _render(request, "portal_track.html", order=order, tickets=tickets,
                   order_id=order_id or "", found=bool(order_id))

