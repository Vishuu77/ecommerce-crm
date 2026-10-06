"""Smoke test for the CRM API — runs against a live server.

    python test_api.py            # starts nothing; expects server on :8000
or use the built-in TestClient (no server needed):
    python test_api.py --local
"""
import sys

def run_with_testclient():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import init_db, SessionLocal
    from app import seed
    # ensure schema + seed exist (startup event also does this)
    init_db()
    db = SessionLocal()
    try:
        seed.seed(db)
    finally:
        db.close()

    c = TestClient(app)
    R = []
    def ck(n, cond, d=""):
        R.append(bool(cond)); print(f"[{'PASS' if cond else 'FAIL'}] {n}" + (f" — {d}" if d else ""))

    ck("health", c.get("/health").json()["status"] == "ok")
    stats = c.get("/api/stats").json()
    ck("seeded products", stats["products"] >= 8, str(stats["products"]))
    ck("seeded order", stats["orders"] >= 2, str(stats["orders"]))

    # product CRUD
    new = {"product_id": "PROD-TST-999", "name": "Test Widget", "category": "Test",
           "price": 100.0, "stock_qty": 5, "return_window_days": 7}
    r = c.post("/api/products", json=new)
    ck("create product", r.status_code == 201, str(r.status_code))
    ck("duplicate product 409", c.post("/api/products", json=new).status_code == 409)
    ck("get product", c.get("/api/products/PROD-TST-999").json()["name"] == "Test Widget")
    upd = dict(new); upd["stock_qty"] = 50
    ck("update product", c.put("/api/products/PROD-TST-999", json=upd).json()["stock_qty"] == 50)
    ck("delete product", c.delete("/api/products/PROD-TST-999").status_code == 204)

    # order CRUD
    from datetime import datetime, timedelta
    o = {"order_id": "ORD-TST-1", "customer_name": "Tester", "customer_email": "t@x.com",
         "product_id": "PROD-EAR-001", "delivery_status": "Delivered", "payment_status": "Paid",
         "delivery_date": (datetime.utcnow() - timedelta(days=3)).isoformat()}
    ck("create order", c.post("/api/orders", json=o).status_code == 201)
    ck("get order", c.get("/api/orders/ORD-TST-1").json()["customer_name"] == "Tester")
    ck("order days_since_delivery", c.get("/api/orders/ORD-TST-1").json()["days_since_delivery"] == 3,
       str(c.get("/api/orders/ORD-TST-1").json().get("days_since_delivery")))
    ck("delete order", c.delete("/api/orders/ORD-TST-1").status_code == 204)

    # ticket CRUD
    t = {"ticket_id": "TCK-TST-1", "order_id": "ORD-98231", "customer_claim": "broken",
         "agent_decision": "Pending", "status": "In-Progress"}
    ck("create ticket", c.post("/api/tickets", json=t).status_code == 201)
    ck("ticket bad order 400", c.post("/api/tickets",
       json={**t, "ticket_id": "TCK-TST-2", "order_id": "NOPE"}).status_code == 400)
    ck("update ticket", c.put("/api/tickets/TCK-TST-1",
       json={**t, "status": "Resolved"}).json()["status"] == "Resolved")
    ck("delete ticket", c.delete("/api/tickets/TCK-TST-1").status_code == 204)

    # UI pages render
    ck("dashboard UI", c.get("/").status_code == 200 and "Dashboard" in c.get("/").text)
    ck("products UI", "Products" in c.get("/ui/products").text)
    ck("orders UI", "Orders" in c.get("/ui/orders").text)
    ck("tickets UI", "Tickets" in c.get("/ui/tickets").text)

    print(f"\n=== {sum(R)}/{len(R)} checks passed ===")
    return 0 if sum(R) == len(R) else 1


def run_live():
    import urllib.request, json
    def get(p):
        return json.load(urllib.request.urlopen(f"http://127.0.0.1:8000{p}"))
    print("health:", get("/health"))
    print("stats:", get("/api/stats"))
    print("products:", len(get("/api/products")))
    return 0


if __name__ == "__main__":
    sys.exit(run_live() if "--live" in sys.argv else run_with_testclient())
