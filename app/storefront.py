"""Storefront: register/login + OTP, browse, cart, checkout, orders, payment.

Customer-facing routes under /shop and /account. Server-side cart (authoritative
prices), transactional stock decrement, and order/payment status.
"""
from __future__ import annotations
import os
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, auth, notify, payments

BASE = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE, "templates"))

router = APIRouter()
SESSION_COOKIE = "shop_session"
OTP_COOKIE = "pending_user"       # signed handle: register -> verify


# ---------------------------------------------------------------- helpers
def current_user(request: Request, db: Session) -> models.User | None:
    uid = auth.read_session(request.cookies.get(SESSION_COOKIE))
    return db.get(models.User, uid) if uid else None


def _render(request, name, **ctx):
    return templates.TemplateResponse(request, name, ctx)


def cart_count(db: Session, user) -> int:
    if not user:
        return 0
    return sum(ci.qty for ci in user.cart_items)


def cart_items(db: Session, user):
    return db.query(models.CartItem).filter(models.CartItem.user_id == user.id).all()


def cart_totals(items):
    subtotal = sum(ci.product.price * ci.qty for ci in items if ci.product)
    return {"subtotal": round(subtotal, 2), "count": sum(ci.qty for ci in items),
            "total": round(subtotal, 2)}


# ---------------------------------------------------------------- auth
@router.get("/shop/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    return _render(request, "shop/register.html", cart_count=cart_count(db, current_user(request, db)))


@router.post("/shop/register", response_class=HTMLResponse)
def register(request: Request, name: str = Form(...), email: str = Form(...),
             phone: str = Form(...), password: str = Form(...),
             db: Session = Depends(get_db)):
    email = email.strip().lower()
    phone_e164 = auth.normalise_phone(phone)
    error = None
    if db.query(models.User).filter(models.User.email == email).first():
        error = "An account with that email already exists."
    elif len(password) < 6:
        error = "Password must be at least 6 characters."
    elif not phone_e164:
        error = "Enter a valid phone number."
    elif db.query(models.User).filter(models.User.phone == phone_e164).first():
        error = "An account with that mobile number already exists."
    if error:
        return _render(request, "shop/register.html", error=error, cart_count=0)

    user = models.User(name=name.strip(), email=email, phone=phone_e164,
                       password_hash=auth.hash_password(password), phone_verified=False)
    db.add(user); db.commit(); db.refresh(user)

    # issue OTP to the phone
    code = auth.generate_otp()
    db.add(models.OTP(phone=phone_e164, code_hash=auth.hash_otp(code),
                      purpose="verify", expires_at=auth.otp_expiry()))
    db.commit()
    notify.send_whatsapp(db, phone_e164,
                         f"Your verification OTP is {code}. Valid 5 minutes.",
                         kind="otp")

    resp = RedirectResponse(f"/shop/verify?phone={phone_e164}", status_code=303)
    # signed handle to *this* registration, so /verify can't land on another
    # account that shares the number
    resp.set_cookie(OTP_COOKIE, auth.make_pending(user.id), max_age=900, httponly=True)
    # dev convenience only — never expose an OTP in production
    if notify.dev_otp_enabled():
        resp.set_cookie("dev_otp", code, max_age=900, httponly=True)
    return resp


@router.get("/shop/verify", response_class=HTMLResponse)
def verify_page(request: Request, phone: str = "", db: Session = Depends(get_db)):
    return _render(request, "shop/verify.html", phone=phone,
                   dev_otp=request.cookies.get("dev_otp", "") if notify.dev_otp_enabled() else "",
                   cart_count=0)


@router.post("/shop/verify", response_class=HTMLResponse)
def verify(request: Request, phone: str = Form(...), code: str = Form(...),
           db: Session = Depends(get_db)):
    phone_e164 = auth.normalise_phone(phone)
    uid = auth.read_pending(request.cookies.get(OTP_COOKIE))
    user = db.get(models.User, uid) if uid else None
    otp = (db.query(models.OTP)
           .filter(models.OTP.phone == phone_e164, models.OTP.consumed == False)  # noqa: E712
           .order_by(models.OTP.created_at.desc()).first())
    error = None
    if not user or user.phone != phone_e164:
        error = "Your verification session expired. Please register again."
    elif not otp:
        error = "No OTP request found for that number."
    elif otp.expires_at < datetime.utcnow():
        error = "OTP expired. Please request a new one."
    elif otp.attempts >= auth.OTP_MAX_ATTEMPTS:
        error = "Too many attempts. Request a new OTP."
    elif not auth.verify_otp_hash(code.strip(), otp.code_hash):
        otp.attempts += 1; db.commit()
        error = "Incorrect OTP."
    if error:
        return _render(request, "shop/verify.html", phone=phone_e164, error=error,
                       dev_otp=request.cookies.get("dev_otp", "") if notify.dev_otp_enabled() else "",
                       cart_count=0)

    otp.consumed = True
    user.phone_verified = True
    db.commit()

    resp = RedirectResponse("/shop", status_code=303)
    resp.set_cookie(SESSION_COOKIE, auth.make_session(user.id),
                    max_age=auth.SESSION_TTL_SECONDS, httponly=True, samesite="lax")
    resp.delete_cookie(OTP_COOKIE)
    resp.delete_cookie("dev_otp")
    return resp


@router.get("/shop/login", response_class=HTMLResponse)
def login_page(request: Request):
    return _render(request, "shop/login.html", cart_count=0)


@router.post("/shop/login", response_class=HTMLResponse)
def login(request: Request, email: str = Form(...), password: str = Form(...),
          db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email.strip().lower()).first()
    if not user or not auth.verify_password(password, user.password_hash):
        return _render(request, "shop/login.html", error="Invalid email or password.", cart_count=0)
    resp = RedirectResponse("/shop", status_code=303)
    resp.set_cookie(SESSION_COOKIE, auth.make_session(user.id),
                    max_age=auth.SESSION_TTL_SECONDS, httponly=True, samesite="lax")
    return resp


@router.post("/shop/logout")
def logout():
    resp = RedirectResponse("/shop", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


# ---------------------------------------------------------------- browse
SORT_LABELS = [("popularity", "Popularity"), ("price_asc", "Price: Low to High"),
               ("price_desc", "Price: High to Low"), ("rating", "Customer Rating"),
               ("discount", "Discount")]
SORT_KEYS = {k for k, _ in SORT_LABELS}


@router.get("/shop", response_class=HTMLResponse)
def shop_home(request: Request, q: str = "", category: str = "", sort: str = "popularity",
              max_price: str = "", db: Session = Depends(get_db)):
    user = current_user(request, db)
    query = db.query(models.Product).filter(models.Product.active == True)  # noqa: E712
    if q:
        like = f"%{q}%"
        query = query.filter((models.Product.name.ilike(like)) |
                             (models.Product.description.ilike(like)) |
                             (models.Product.category.ilike(like)))
    if category:
        query = query.filter(models.Product.category == category)
    if max_price:
        try:
            query = query.filter(models.Product.price <= float(max_price))
        except ValueError:
            max_price = ""

    products = query.all()
    if sort == "discount":
        products.sort(key=lambda p: p.discount_pct, reverse=True)
    elif sort in SORT_KEYS:
        products.sort(key=_sort_key(sort))

    cats = [c[0] for c in db.query(models.Product.category).distinct().all()]
    return _render(request, "shop/home.html", products=products, q=q, category=category,
                   sort=sort, max_price=max_price, sorts=SORT_LABELS, categories=cats,
                   user=user, cart_count=cart_count(db, user))


def _sort_key(sort: str):
    if sort == "price_asc":
        return lambda p: p.price
    if sort == "price_desc":
        return lambda p: -p.price
    if sort == "rating":
        return lambda p: -p.rating
    return lambda p: -p.review_count


@router.get("/shop/product/{product_id}", response_class=HTMLResponse)
def product_page(product_id: str, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    p = db.get(models.Product, product_id)
    if not p:
        raise HTTPException(404, "product not found")
    related = (db.query(models.Product)
               .filter(models.Product.category == p.category,
                       models.Product.product_id != p.product_id,
                       models.Product.active == True)  # noqa: E712
               .limit(4).all())
    return _render(request, "shop/product.html", p=p, related=related, user=user,
                   cart_count=cart_count(db, user))


# ---------------------------------------------------------------- cart
@router.get("/shop/cart", response_class=HTMLResponse)
def cart_page(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/shop/login?next=/shop/cart", status_code=303)
    items = cart_items(db, user)
    return _render(request, "shop/cart.html", items=items, totals=cart_totals(items),
                   user=user, cart_count=cart_count(db, user))


@router.post("/shop/cart/add")
def cart_add(request: Request, product_id: str = Form(...), qty: int = Form(1),
             db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/shop/login?next=/shop", status_code=303)
    p = db.get(models.Product, product_id)
    if not p or p.stock_qty <= 0:
        return RedirectResponse("/shop", status_code=303)
    qty = max(1, min(qty, p.stock_qty))
    ci = (db.query(models.CartItem)
          .filter(models.CartItem.user_id == user.id,
                  models.CartItem.product_id == product_id).first())
    if ci:
        ci.qty = min(ci.qty + qty, p.stock_qty)
    else:
        db.add(models.CartItem(user_id=user.id, product_id=product_id, qty=qty))
    db.commit()
    return RedirectResponse(request.headers.get("referer", "/shop/cart"), status_code=303)


@router.post("/shop/cart/update")
def cart_update(request: Request, item_id: int = Form(...), qty: int = Form(...),
                db: Session = Depends(get_db)):
    user = current_user(request, db)
    ci = db.get(models.CartItem, item_id)
    if user and ci and ci.user_id == user.id:
        if qty <= 0:
            db.delete(ci)
        else:
            ci.qty = min(qty, ci.product.stock_qty)
        db.commit()
    return RedirectResponse("/shop/cart", status_code=303)


@router.post("/shop/cart/remove")
def cart_remove(request: Request, item_id: int = Form(...), db: Session = Depends(get_db)):
    user = current_user(request, db)
    ci = db.get(models.CartItem, item_id)
    if user and ci and ci.user_id == user.id:
        db.delete(ci); db.commit()
    return RedirectResponse("/shop/cart", status_code=303)


# ---------------------------------------------------------------- checkout
@router.get("/shop/checkout", response_class=HTMLResponse)
def checkout_page(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/shop/login?next=/shop/checkout", status_code=303)
    items = cart_items(db, user)
    if not items:
        return RedirectResponse("/shop/cart", status_code=303)
    return _render(request, "shop/checkout.html", items=items, totals=cart_totals(items),
                   user=user, cart_count=cart_count(db, user), pay_mode=payments.mode())


@router.post("/shop/checkout")
def checkout(request: Request, address: str = Form(...), phone: str = Form(""),
             db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/shop/login?next=/shop/checkout", status_code=303)
    items = cart_items(db, user)
    if not items:
        return RedirectResponse("/shop/cart", status_code=303)

    # ---- validate stock atomically-ish and build the order
    total = 0.0
    for ci in items:
        if not ci.product or ci.product.stock_qty < ci.qty:
            return _render(request, "shop/checkout.html", items=items,
                           totals=cart_totals(items), user=user,
                           cart_count=cart_count(db, user), pay_mode=payments.mode(),
                           error=f"{ci.product.name if ci.product else 'An item'} "
                                 f"is out of stock for the requested quantity.")

    order = models.Order(
        order_id="ORD-" + datetime.utcnow().strftime("%y%m%d%H%M%S") + str(user.id % 100),
        user_id=user.id, customer_name=user.name, customer_email=user.email,
        customer_phone=auth.normalise_phone(phone) or user.phone,
        shipping_address=address, order_date=datetime.utcnow(),
        delivery_status="Pending", payment_status="Pending")

    for ci in items:
        line = ci.product.price * ci.qty
        total += line
        order.items.append(models.OrderItem(
            product_id=ci.product_id, name=ci.product.name,
            unit_price=ci.product.price, qty=ci.qty, line_total=round(line, 2)))
    order.total_amount = round(total, 2)
    db.add(order)

    # decrement stock (commit happens below, single transaction)
    for ci in items:
        ci.product.stock_qty -= ci.qty
    # clear the cart
    for ci in items:
        db.delete(ci)
    db.commit()
    db.refresh(order)

    # create a payment intent
    pay = payments.create_order(order.total_amount, order.order_id)
    db.add(models.Payment(order_id=order.order_id, provider=pay["provider"],
                          provider_order_id=pay["id"], amount=order.total_amount,
                          status="created"))
    db.commit()
    notify.notify_order(db, order, kind="order")
    return RedirectResponse(f"/shop/pay/{order.order_id}", status_code=303)


# ---------------------------------------------------------------- payment
@router.get("/shop/pay/{order_id}", response_class=HTMLResponse)
def pay_page(order_id: str, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    order = db.get(models.Order, order_id)
    if not order or (user and order.user_id != user.id):
        raise HTTPException(404, "order not found")
    pay = db.query(models.Payment).filter(models.Payment.order_id == order_id).first()
    return _render(request, "shop/pay.html", order=order, pay=pay, user=user,
                   key_id=payments.KEY_ID, live=payments.live(),
                   cart_count=cart_count(db, user))


@router.post("/shop/pay/{order_id}/confirm", response_class=HTMLResponse)
def pay_confirm(order_id: str, request: Request,
                razorpay_payment_id: str = Form(""),
                razorpay_order_id: str = Form(""),
                razorpay_signature: str = Form(""),
                db: Session = Depends(get_db)):
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(404, "order not found")
    pay = db.query(models.Payment).filter(models.Payment.order_id == order_id).first()

    ok = payments.verify_signature(razorpay_order_id or (pay.provider_order_id if pay else ""),
                                   razorpay_payment_id or ("sim_" + order_id),
                                   razorpay_signature)
    if ok:
        order.payment_status = "Paid"
        if pay:
            pay.status = "paid"
            pay.provider_payment_id = razorpay_payment_id or pay.provider_order_id
        db.commit()
        notify.notify_order(db, order, kind="payment")
        return RedirectResponse(f"/shop/order/{order_id}", status_code=303)

    order.payment_status = "Failed"
    if pay:
        pay.status = "failed"
    db.commit()
    notify.notify_order(db, order, kind="payment")
    return RedirectResponse(f"/shop/pay/{order_id}", status_code=303)


# ---------------------------------------------------------------- orders
@router.get("/shop/orders", response_class=HTMLResponse)
def my_orders(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/shop/login?next=/shop/orders", status_code=303)
    orders = (db.query(models.Order).filter(models.Order.user_id == user.id)
              .order_by(models.Order.order_date.desc()).all())
    return _render(request, "shop/orders.html", orders=orders, user=user,
                   cart_count=cart_count(db, user))


@router.get("/shop/order/{order_id}", response_class=HTMLResponse)
def order_detail(order_id: str, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    order = db.get(models.Order, order_id)
    if not order or (user and order.user_id != user.id):
        raise HTTPException(404, "order not found")
    pay = db.query(models.Payment).filter(models.Payment.order_id == order_id).first()
    notifs = (db.query(models.Notification)
              .filter(models.Notification.order_id == order_id)
              .order_by(models.Notification.created_at.desc()).all())
    return _render(request, "shop/order.html", order=order, pay=pay, notifs=notifs,
                   user=user, cart_count=cart_count(db, user))
