"""Storefront tests: register/login, browse, cart, checkout, orders."""
from datetime import datetime

from app import auth


def _register(client, email="new@example.com", phone="9876500000", password="secret123",
              name="New User"):
    """Register -> immediately signed in (no OTP step)."""
    r = client.post("/shop/register", data={
        "name": name, "email": email, "phone": phone, "password": password},
        follow_redirects=False)
    assert r.status_code == 303
    assert r.cookies.get("shop_session"), "register should sign the customer in"
    return client


# ---------------------------------------------------------------- browse
def test_shop_home_loads(client):
    r = client.get("/shop")
    assert r.status_code == 200 and "ShopKart" in r.text
    assert "AeroSound" in r.text


def test_product_page(client):
    r = client.get("/shop/product/PROD-EAR-001")
    assert r.status_code == 200 and "AeroSound" in r.text


def test_product_404(client):
    assert client.get("/shop/product/NOPE").status_code == 404


def test_search(client):
    r = client.get("/shop?q=earbuds")
    assert "AeroSound" in r.text


def test_sort_price_ascending(client):
    r = client.get("/shop?sort=price_asc")
    import re
    prices = [float(x.replace(",", "")) for x in re.findall(r'class="price">₹([\d,]+)', r.text)]
    assert prices == sorted(prices) and len(prices) > 1


def test_category_filter(client):
    r = client.get("/shop?category=Books")
    assert "Python Made Simple" in r.text and "AeroSound" not in r.text


def test_price_filter(client):
    r = client.get("/shop?max_price=499")
    assert "Python Made Simple" in r.text and "PulseFit Smartwatch" not in r.text


def test_images_served(client):
    r = client.get("/static/products/PROD-EAR-001.svg")
    assert r.status_code == 200 and "svg" in r.text.lower()


# ---------------------------------------------------------------- auth
def test_register_signs_in_and_creates_account(client):
    _register(client)
    from app.database import SessionLocal
    from app import models
    db = SessionLocal()
    u = db.query(models.User).filter(models.User.email == "new@example.com").first()
    assert u is not None and u.phone == "+919876500000"
    db.close()
    # session works
    assert client.get("/shop/cart").status_code == 200


def test_register_duplicate_email_rejected(client):
    data = {"name": "D", "email": "dup@example.com", "phone": "9990001111", "password": "pass123"}
    client.post("/shop/register", data=data, follow_redirects=False)
    r = client.post("/shop/register", data=data, follow_redirects=False)
    assert r.status_code == 200 and "already exists" in r.text


def test_register_duplicate_phone_rejected(client):
    """phone is unique — a second account can't claim the same number."""
    data = {"name": "P1", "email": "p1@example.com", "phone": "9111000001", "password": "pass123"}
    assert client.post("/shop/register", data=data, follow_redirects=False).status_code == 303
    r = client.post("/shop/register",
                    data={**data, "email": "p2@example.com"}, follow_redirects=False)
    assert r.status_code == 200 and "mobile number already exists" in r.text


def test_register_short_password_rejected(client):
    r = client.post("/shop/register", data={
        "name": "S", "email": "s@example.com", "phone": "9000000009", "password": "123"},
        follow_redirects=False)
    assert r.status_code == 200 and "at least 6 characters" in r.text


def test_login_demo_user(client):
    r = client.post("/shop/login", data={"email": "vishnu@example.com", "password": "demo1234"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.cookies.get("shop_session")


def test_login_wrong_password(client):
    r = client.post("/shop/login", data={"email": "vishnu@example.com", "password": "nope"})
    assert "Invalid email or password" in r.text


def test_logout(client):
    _register(client, email="lo@example.com", phone="9000000010")
    r = client.post("/shop/logout", follow_redirects=False)
    assert r.status_code == 303
    assert not r.cookies.get("shop_session")


# ---------------------------------------------------------------- cart + checkout
def test_full_purchase_flow(client):
    _register(client, email="buyer@example.com", phone="9123456780")

    r = client.post("/shop/cart/add", data={"product_id": "PROD-EAR-001", "qty": 2},
                    follow_redirects=False)
    assert r.status_code == 303
    cart = client.get("/shop/cart")
    assert "AeroSound" in cart.text

    from app.database import SessionLocal
    from app import models
    db = SessionLocal()
    before = db.get(models.Product, "PROD-EAR-001").stock_qty
    db.close()

    # checkout places the order directly (no payment step)
    r = client.post("/shop/checkout", data={"address": "1 Test St, Bengaluru", "phone": "9123456780"},
                    follow_redirects=False)
    assert r.status_code == 303 and "/shop/order/" in r.headers["location"]
    order_id = r.headers["location"].rsplit("/", 1)[-1]

    db = SessionLocal()
    after = db.get(models.Product, "PROD-EAR-001").stock_qty
    order = db.get(models.Order, order_id)
    assert after == before - 2
    assert order.total_amount == 2499.0 * 2
    assert len(order.items) == 1
    assert order.delivery_status == "Pending"
    db.close()

    detail = client.get(f"/shop/order/{order_id}")
    assert "AeroSound" in detail.text and "Delivery: Pending" in detail.text


def test_checkout_requires_login(client):
    r = client.post("/shop/checkout", data={"address": "x"}, follow_redirects=False)
    assert r.status_code == 303 and "/shop/login" in r.headers["location"]


def test_cart_requires_login(client):
    r = client.get("/shop/cart", follow_redirects=False)
    assert r.status_code == 303 and "/shop/login" in r.headers["location"]


def test_cart_add_respects_stock(client):
    _register(client, email="stock@example.com", phone="9123456781")
    # PROD-PB-003 has 8 in stock; ask for 999
    client.post("/shop/cart/add", data={"product_id": "PROD-PB-003", "qty": 999},
                follow_redirects=False)
    cart = client.get("/shop/cart")
    assert 'value="8"' in cart.text


def test_cart_update_and_remove(client):
    _register(client, email="cu@example.com", phone="9123456782")
    client.post("/shop/cart/add", data={"product_id": "PROD-BK-006", "qty": 1},
                follow_redirects=False)
    from app.database import SessionLocal
    from app import models
    db = SessionLocal()
    u = db.query(models.User).filter(models.User.email == "cu@example.com").first()
    ci = (db.query(models.CartItem)
          .filter(models.CartItem.user_id == u.id,
                  models.CartItem.product_id == "PROD-BK-006").first())
    item_id = ci.id
    db.close()
    client.post("/shop/cart/update", data={"item_id": item_id, "qty": 3}, follow_redirects=False)
    db = SessionLocal()
    assert db.get(models.CartItem, item_id).qty == 3
    db.close()
    client.post("/shop/cart/remove", data={"item_id": item_id}, follow_redirects=False)
    db = SessionLocal()
    assert db.get(models.CartItem, item_id) is None
    db.close()


def test_orders_page_requires_login(client):
    r = client.get("/shop/orders", follow_redirects=False)
    assert r.status_code == 303


def test_my_orders_lists_own_orders(client):
    _register(client, email="mine@example.com", phone="9123456783")
    client.post("/shop/cart/add", data={"product_id": "PROD-CC-005", "qty": 1},
                follow_redirects=False)
    client.post("/shop/checkout", data={"address": "x"}, follow_redirects=False)
    r = client.get("/shop/orders")
    assert r.status_code == 200 and "ORD-" in r.text
