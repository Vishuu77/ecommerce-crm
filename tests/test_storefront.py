"""Storefront tests: auth + OTP, browse, cart, checkout, payment, orders."""
from datetime import datetime

from app import auth


def _register_and_verify(client, email="new@example.com", phone="9876500000",
                         password="secret123"):
    """Helper: register -> read dev OTP -> verify -> returns authed client."""
    r = client.post("/shop/register", data={
        "name": "New User", "email": email, "phone": phone, "password": password},
        follow_redirects=False)
    assert r.status_code == 303
    dev_otp = r.cookies.get("dev_otp")
    assert dev_otp, "dev OTP cookie should be set when no WA channel configured"
    r2 = client.post("/shop/verify", data={"phone": phone, "code": dev_otp},
                     follow_redirects=False)
    assert r2.status_code == 303
    return client


# ---------------------------------------------------------------- auth
def test_shop_home_loads(client):
    r = client.get("/shop")
    assert r.status_code == 200 and "ShopKart" in r.text
    assert "AeroSound" in r.text


def test_register_sets_dev_otp(client):
    r = client.post("/shop/register", data={
        "name": "A", "email": "a@example.com", "phone": "9998887776", "password": "pass123"},
        follow_redirects=False)
    assert r.status_code == 303
    assert r.cookies.get("dev_otp")
    assert "/shop/verify" in r.headers["location"]


def test_register_duplicate_email_rejected(client):
    data = {"name": "D", "email": "dup@example.com", "phone": "9990001111", "password": "pass123"}
    client.post("/shop/register", data=data, follow_redirects=False)
    r = client.post("/shop/register", data=data, follow_redirects=False)
    assert r.status_code == 200 and "already exists" in r.text


def test_verify_wrong_otp_fails(client):
    client.post("/shop/register", data={
        "name": "B", "email": "b@example.com", "phone": "9000000001", "password": "pass123"},
        follow_redirects=False)
    r = client.post("/shop/verify", data={"phone": "9000000001", "code": "000000"})
    assert "Incorrect OTP" in r.text


def test_register_duplicate_phone_rejected(client):
    """phone is unique — a second account can't claim the same number."""
    data = {"name": "P1", "email": "p1@example.com", "phone": "9111000001", "password": "pass123"}
    assert client.post("/shop/register", data=data, follow_redirects=False).status_code == 303
    r = client.post("/shop/register",
                    data={**data, "email": "p2@example.com"}, follow_redirects=False)
    assert r.status_code == 200 and "mobile number already exists" in r.text


def test_verify_logs_in_the_registrant_not_another_account(client):
    """Regression: verify() looked the user up by phone, so with two accounts on
    one number it verified (and logged in) whichever row came back first."""
    r = client.post("/shop/register", data={
        "name": "Registrant", "email": "reg@example.com",
        "phone": "9111000002", "password": "pass123"}, follow_redirects=False)
    dev = r.cookies.get("dev_otp")
    r2 = client.post("/shop/verify", data={"phone": "9111000002", "code": dev},
                     follow_redirects=False)
    assert r2.status_code == 303
    from app.database import SessionLocal
    from app import models
    db = SessionLocal()
    uid = auth.read_session(r2.cookies.get("shop_session"))
    user = db.get(models.User, uid)
    assert user.email == "reg@example.com" and user.phone_verified
    db.close()


def test_verify_without_pending_cookie_rejected(client):
    r = client.post("/shop/verify", data={"phone": "9111000003", "code": "123456"})
    assert "session expired" in r.text


def test_login_demo_user(client):
    r = client.post("/shop/login", data={"email": "vishnu@example.com", "password": "demo1234"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.cookies.get("shop_session")


def test_login_wrong_password(client):
    r = client.post("/shop/login", data={"email": "vishnu@example.com", "password": "nope"})
    assert "Invalid email or password" in r.text


# ---------------------------------------------------------------- cart + checkout
def test_full_purchase_flow(client):
    _register_and_verify(client, email="buyer@example.com", phone="9123456780")

    # add to cart
    r = client.post("/shop/cart/add", data={"product_id": "PROD-EAR-001", "qty": 2},
                    follow_redirects=False)
    assert r.status_code == 303
    cart = client.get("/shop/cart")
    assert "AeroSound" in cart.text

    # checkout -> order created, stock decremented
    from app.database import SessionLocal
    from app import models
    db = SessionLocal()
    before = db.get(models.Product, "PROD-EAR-001").stock_qty
    db.close()

    r = client.post("/shop/checkout", data={"address": "1 Test St, Bengaluru", "phone": "9123456780"},
                    follow_redirects=False)
    assert r.status_code == 303 and "/shop/pay/" in r.headers["location"]
    order_id = r.headers["location"].rsplit("/", 1)[-1]

    db = SessionLocal()
    after = db.get(models.Product, "PROD-EAR-001").stock_qty
    order = db.get(models.Order, order_id)
    assert after == before - 2
    assert order.total_amount == 2499.0 * 2
    assert len(order.items) == 1
    db.close()

    # pay (simulate)
    r = client.post(f"/shop/pay/{order_id}/confirm", data={}, follow_redirects=False)
    assert r.status_code == 303
    detail = client.get(f"/shop/order/{order_id}")
    assert "Paid" in detail.text


def test_checkout_requires_login(client):
    r = client.post("/shop/checkout", data={"address": "x"}, follow_redirects=False)
    assert r.status_code == 303 and "/shop/login" in r.headers["location"]


def test_cart_requires_login(client):
    r = client.get("/shop/cart", follow_redirects=False)
    assert r.status_code == 303 and "/shop/login" in r.headers["location"]


# ---------------------------------------------------------------- misc pages
def test_product_page(client):
    r = client.get("/shop/product/PROD-EAR-001")
    assert r.status_code == 200 and "AeroSound" in r.text


def test_product_404(client):
    assert client.get("/shop/product/NOPE").status_code == 404


def test_orders_page_requires_login(client):
    r = client.get("/shop/orders", follow_redirects=False)
    assert r.status_code == 303


def test_search(client):
    r = client.get("/shop?q=earbuds")
    assert "AeroSound" in r.text
