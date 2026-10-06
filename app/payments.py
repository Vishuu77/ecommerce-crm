"""Payments: Razorpay (India — UPI/cards/netbanking) with a working simulate path.

If RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are set, real Razorpay orders are created
and signatures verified. Otherwise the app runs in simulate mode so the full
cart -> checkout -> paid flow is demonstrable end-to-end without keys.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
import secrets
import urllib.request

KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")


def live() -> bool:
    return bool(KEY_ID and KEY_SECRET)


def create_order(amount_inr: float, receipt: str) -> dict:
    """Create a payment order. Returns {id, amount, currency, provider, key}."""
    amount_paise = int(round(amount_inr * 100))
    if not live():
        return {"provider": "simulate", "id": "sim_" + secrets.token_hex(8),
                "amount": amount_paise, "currency": "INR", "key": None}
    payload = {"amount": amount_paise, "currency": "INR",
               "receipt": receipt, "payment_capture": 1}
    auth = base64.b64encode(f"{KEY_ID}:{KEY_SECRET}".encode()).decode()
    req = urllib.request.Request(
        "https://api.razorpay.com/v1/orders",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    data["provider"] = "razorpay"
    data["key"] = KEY_ID
    return data


def verify_signature(razorpay_order_id: str, razorpay_payment_id: str, signature: str) -> bool:
    """Verify the Razorpay checkout callback signature."""
    if not live():
        return True     # simulate mode: nothing to verify
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected = hmac.new(KEY_SECRET.encode(), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def mode() -> str:
    return "razorpay (live keys)" if live() else "simulate (no keys configured)"
