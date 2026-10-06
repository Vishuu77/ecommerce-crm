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

## Two interfaces

**Storefront (ShopKart)** — what a customer buys from
- `/shop` — catalog: search, category, price filter, sort, ratings, discounts
- `/shop/product/{id}` — detail page with related products
- `/shop/cart` → `/shop/checkout` → `/shop/pay/{order}` → `/shop/order/{order}`
- `/shop/register` → OTP → verified account; `/shop/orders` order history

**Staff / Admin CRM** — manage everything
- `/` dashboard, `/ui/products`, `/ui/orders`, `/ui/tickets`
- Full CRUD REST API at `/api/*`, docs at `/docs`

**Returns Portal** — self-service returns
- `/portal` — home + policy summary
- `/portal/order` — raise a replacement/refund request
- `/portal/track` — track a request's status

### How a customer buys
1. `/shop` — browse, filter, sort; add items to a server-side cart.
2. `/shop/register` — name, email, mobile. An **OTP is sent to that mobile**
   (WhatsApp). Verify it and the account is active and logged in.
3. `/shop/checkout` — delivery address + phone, stock validated and decremented
   in one transaction.
4. `/shop/pay/{order}` — Razorpay (UPI / cards / netbanking). Without keys the
   app runs in **simulate mode** so the full paid flow is demonstrable.
5. Order status updates are pushed to the customer's mobile over WhatsApp.

### How a customer gets a replacement
1. Open `/portal/order`, enter the Order ID (e.g. `ORD-98231`).
2. Pick what went wrong (damaged / defective / wrong item / not needed).
3. Describe the issue and upload proof (photo or short video).
4. The policy engine checks it instantly:
   - delivered? · inside the return window? · DOA (48–72h)? · proof attached?
   - **Replacement approved** if in stock, **refund** if out of stock.
5. A ticket is created and visible to staff; the customer tracks it at `/portal/track`.

## Return policy (enforced in code — `app/policy.py`)

| Rule | Value |
|---|---|
| DOA (damaged/defective on arrival) | report within 48–72 hours |
| Standard return window | 7 days from delivery (per product) |
| Proof | photo/video required |
| Remedy priority | replacement first, refund only if out of stock |
| Refund timing | 5–7 business days to original payment method |

## Run locally

```bash
cd ecommerce-crm
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:
- Customer portal → http://127.0.0.1:8000/portal
- Staff CRM       → http://127.0.0.1:8000/
- API docs        → http://127.0.0.1:8000/docs

The database (`app/crm.db`) is created and seeded automatically on first start.

## Test

```bash
python -m pytest              # 50 tests: API + policy + portal + auth + storefront
```

## Environment variables

| Var | Purpose |
|---|---|
| `DATABASE_URL` | `sqlite:///...` (default) or `postgresql+psycopg://...` |
| `APP_SECRET` | session/OTP signing key — **set this in production** |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | live payments; omit for simulate mode |
| `WA_BRIDGE_URL` | local WhatsApp bridge (default `http://127.0.0.1:8765`) |
| `WA_TOKEN` / `WA_PHONE_ID` | Meta WhatsApp Cloud API (alternative to the bridge) |

Notifications always write a row to `notifications` (audit trail); delivery is
best-effort — bridge, then Cloud API, then logged as `simulated`.

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
Products     (product_id PK, name, category, price, mrp, rating, review_count,
              stock_qty, return_window_days, description, image_url, active)
Users        (id PK, name, email UNIQUE, phone UNIQUE, password_hash,
              phone_verified, created_at)
OTP          (id PK, phone, code_hash, purpose, expires_at, attempts, consumed)
CartItem     (id PK, user_id FK, product_id FK, qty)  — UNIQUE(user, product)
Orders       (order_id PK, user_id FK, customer_name, customer_email,
              customer_phone, shipping_address, order_date, delivery_date,
              delivery_status, payment_status, total_amount)
OrderItem    (id PK, order_id FK, product_id FK, name, unit_price, qty, line_total)
Payment      (id PK, order_id FK, provider, provider_order_id,
              provider_payment_id, amount, currency, status)
Tickets      (ticket_id PK, order_id FK, customer_claim, proof_url,
              agent_decision, policy_checks, status, updated_at)
Notification (id PK, channel, to, kind, body, status, error, order_id, created_at)
```

Note: SQLite is created with `create_all` on startup — there are no migrations.
For an existing DB, add the new `products` columns (`mrp`, `rating`,
`review_count`) manually or delete `app/crm.db` to reseed.

## Stack

FastAPI · SQLAlchemy 2.0 · Pydantic v2 · Jinja2 · Uvicorn · SQLite/Postgres
