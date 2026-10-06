"""Notifications: WhatsApp (via the local bridge or Meta Cloud API), SMS, email.

Always writes a Notification row (audit trail). Delivery is best-effort:
  - WhatsApp: POST to WA_BRIDGE_URL if the Baileys bridge exposes /send,
              else Meta Cloud API if WA_TOKEN/WA_PHONE_ID set,
              else log as 'simulated' (dev) — never crashes the request.
"""
from __future__ import annotations
import json
import os
import urllib.request

from sqlalchemy.orm import Session
from app import models

WA_BRIDGE_URL = os.environ.get("WA_BRIDGE_URL", "http://127.0.0.1:8765")
WA_TOKEN = os.environ.get("WA_TOKEN", "")            # Meta Cloud API
WA_PHONE_ID = os.environ.get("WA_PHONE_ID", "")


def dev_otp_enabled() -> bool:
    """Whether to surface OTPs in the UI / a dev cookie.

    Production-safe default: off whenever a real WhatsApp channel is
    configured, because an exposed OTP lets anyone take over an account.
    `DEV_OTP` overrides explicitly (`1`/`true` on, `0`/`false` off).

    Reads os.environ live (not the module constants, which are captured at
    import) so tests and late env changes behave predictably.
    """
    raw = os.environ.get("DEV_OTP")
    if raw is not None:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    has_cloud = bool(os.environ.get("WA_TOKEN")) and bool(os.environ.get("WA_PHONE_ID"))
    has_bridge = bool(os.environ.get("WA_BRIDGE_URL"))
    return not has_cloud and not has_bridge


def _log(db: Session, channel, to, kind, body, status, error="", order_id=""):
    n = models.Notification(channel=channel, to=to, kind=kind, body=body,
                            status=status, error=error, order_id=order_id)
    db.add(n)
    db.commit()
    return n


def send_whatsapp(db: Session, to: str, body: str, kind: str = "", order_id: str = "") -> dict:
    """Send a WhatsApp message; record the attempt regardless of outcome."""
    to = to or ""
    bridge_err = ""

    # 1) local Baileys bridge
    try:
        req = urllib.request.Request(
            WA_BRIDGE_URL.rstrip("/") + "/send",
            data=json.dumps({"to": to, "text": body}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=6) as r:
            if r.status == 200:
                _log(db, "whatsapp", to, kind, body, "sent", order_id=order_id)
                return {"status": "sent", "via": "bridge"}
    except Exception as e:
        bridge_err = str(e)

    # 2) Meta Cloud API
    if WA_TOKEN and WA_PHONE_ID:
        try:
            payload = {"messaging_product": "whatsapp", "to": to.replace("+", ""),
                       "type": "text", "text": {"body": body}}
            req = urllib.request.Request(
                f"https://graph.facebook.com/v20.0/{WA_PHONE_ID}/messages",
                data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {WA_TOKEN}",
                         "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.status == 200:
                    _log(db, "whatsapp", to, kind, body, "sent", order_id=order_id)
                    return {"status": "sent", "via": "cloud_api"}
        except Exception as e:
            _log(db, "whatsapp", to, kind, body, "failed", str(e), order_id)
            return {"status": "failed", "error": str(e)}

    # 3) dev fallback — record and surface in logs / admin
    _log(db, "whatsapp", to, kind, body, "simulated",
         error=bridge_err or "no channel configured", order_id=order_id)
    return {"status": "simulated", "note": "no WhatsApp channel configured; logged to DB"}


def notify_order(db: Session, order, kind: str = "order"):
    """Send an order/payment status update to the customer."""
    to = getattr(order, "customer_phone", "") or ""
    lines = [f"Hi {order.customer_name},",
             f"Order {order.order_id}: {order.delivery_status} / Payment: {order.payment_status}"]
    if getattr(order, "total_amount", 0):
        lines.append(f"Total: Rs.{order.total_amount:.0f}")
    lines.append("Track: /portal/track?order_id=" + order.order_id)
    return send_whatsapp(db, to, "\n".join(lines), kind=kind, order_id=order.order_id)
