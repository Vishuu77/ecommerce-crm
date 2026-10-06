# E-commerce CRM

A local-first, cloud-ready CRM for an online store — **Products, Orders, and Returns/Tickets**.
FastAPI + SQLite (local) or Postgres (cloud), with a JSON API and a server-rendered admin UI.

Part of the **Return & Refund Harness** roadmap (`Harness project.docx`).

## Features

- **Products** — CRUD, stock levels, return window, stock status (In / Low / Out)
- **Orders** — CRUD, delivery + payment status, days-since-delivery
- **Returns & Tickets** — log complaints with proof upload, track decision + status
- **Dashboard** — live counts, order value, low-stock and open-ticket alerts
- **JSON API** — full REST CRUD at `/api/*` with interactive docs at `/docs`
- **Admin UI** — dark-themed server-rendered pages at `/`
- **Cloud-ready** — one `DATABASE_URL` env var switches SQLite → Postgres

## Run locally

```bash
cd ecommerce-crm
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:
- Admin UI  → http://127.0.0.1:8000/
- API docs  → http://127.0.0.1:8000/docs
- Health    → http://127.0.0.1:8000/health

The database (`app/crm.db`) is created and seeded automatically on first start.

## Test

```bash
python test_api.py           # 20 checks via TestClient (no server needed)
python test_api.py --live    # hit a running server on :8000
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/stats` | dashboard counts |
| GET/POST | `/api/products` | list / create |
| GET/PUT/DELETE | `/api/products/{id}` | read / update / delete |
| GET/POST | `/api/orders` | list / create |
| GET/PUT/DELETE | `/api/orders/{id}` | read / update / delete |
| GET/POST | `/api/tickets` | list / create |
| GET/PUT/DELETE | `/api/tickets/{id}` | read / update / delete |

## Deploy

### Render (recommended — no Docker needed)

1. Push this repo to GitHub.
2. Render Dashboard → **New → Blueprint** → pick the repo (`render.yaml` is included).
   Or **New → Web Service** → Build: `pip install -r requirements.txt`,
   Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. (Optional, for persistent data) add a Postgres instance and set `DATABASE_URL`.
   Without it, SQLite is used and data resets on redeploy.

### Docker

```bash
docker build -t ecommerce-crm .
docker run -p 8000:8000 ecommerce-crm
```

### Railway / Fly.io

`Procfile` and `Dockerfile` are included; both platforms auto-detect them.

## Schema

```
Products   (product_id PK, name, category, price, stock_qty, return_window_days)
Orders     (order_id PK, customer_name, customer_email, product_id FK,
            order_date, delivery_date, delivery_status, payment_status)
Tickets    (ticket_id PK, order_id FK, customer_claim, proof_url,
            agent_decision, policy_checks, status, updated_at)
```

## Next steps (roadmap)

- Agent harness layer: `get_order_details`, `check_policy_compliance`,
  `analyze_image_proof`, `update_sheet_record`
- Return-policy engine (7-day window, DOA 48–72h, replacement-first)
- Idempotency guard against duplicate tickets/refunds

## Stack

FastAPI · SQLAlchemy 2.0 · Pydantic v2 · Jinja2 · Uvicorn · SQLite/Postgres
