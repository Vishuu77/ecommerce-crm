"""API tests: products, orders, tickets, stats, health."""
from datetime import datetime, timedelta


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_seeded(client):
    s = client.get("/api/stats").json()
    assert s["products"] >= 8 and s["orders"] >= 2


def test_openapi_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    for p in ("/api/products", "/api/orders", "/api/tickets", "/api/stats"):
        assert p in paths


# ---------------------------------------------------------------- products
def test_product_crud(client):
    new = {"product_id": "PROD-T1", "name": "Widget", "category": "Test",
           "price": 100.0, "stock_qty": 5, "return_window_days": 7}
    assert client.post("/api/products", json=new).status_code == 201
    assert client.post("/api/products", json=new).status_code == 409      # duplicate
    assert client.get("/api/products/PROD-T1").json()["name"] == "Widget"
    upd = {**new, "stock_qty": 50}
    assert client.put("/api/products/PROD-T1", json=upd).json()["stock_qty"] == 50
    assert client.delete("/api/products/PROD-T1").status_code == 204
    assert client.get("/api/products/PROD-T1").status_code == 404


def test_stock_status(client):
    assert client.get("/api/products/PROD-EAR-001").json()["stock_status"] == "In Stock"
    assert client.get("/api/products/PROD-HK-007").json()["stock_status"] == "Low Stock"


# ---------------------------------------------------------------- orders
def test_order_crud_and_days_since_delivery(client):
    o = {"order_id": "ORD-T1", "customer_name": "T", "customer_email": "t@x.com",
         "product_id": "PROD-EAR-001", "delivery_status": "Delivered",
         "payment_status": "Paid",
         "delivery_date": (datetime.utcnow() - timedelta(days=3)).isoformat()}
    assert client.post("/api/orders", json=o).status_code == 201
    got = client.get("/api/orders/ORD-T1").json()
    assert got["customer_name"] == "T"
    assert got["days_since_delivery"] == 3
    assert client.delete("/api/orders/ORD-T1").status_code == 204


# ---------------------------------------------------------------- tickets
def test_ticket_crud_and_validation(client):
    t = {"ticket_id": "TCK-T1", "order_id": "ORD-98231", "customer_claim": "broken",
         "agent_decision": "Pending", "status": "In-Progress"}
    assert client.post("/api/tickets", json=t).status_code == 201
    bad = {**t, "ticket_id": "TCK-T2", "order_id": "NOPE"}
    assert client.post("/api/tickets", json=bad).status_code == 400      # bad order FK
    assert client.put("/api/tickets/TCK-T1", json={**t, "status": "Resolved"}
                      ).json()["status"] == "Resolved"
    assert client.delete("/api/tickets/TCK-T1").status_code == 204


# ---------------------------------------------------------------- UI
def test_ui_pages_render(client):
    for url in ("/", "/ui/products", "/ui/orders", "/ui/tickets"):
        r = client.get(url)
        assert r.status_code == 200
        assert "Traceback" not in r.text
