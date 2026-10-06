"""Auth/notify/payment unit tests."""
import time
from datetime import datetime, timedelta

from app import auth, notify, payments


def test_password_hash_roundtrip():
    h = auth.hash_password("s3cret!")
    assert auth.verify_password("s3cret!", h)
    assert not auth.verify_password("wrong", h)


def test_password_hash_is_salted():
    assert auth.hash_password("x") != auth.hash_password("x")


def test_phone_normalisation():
    assert auth.normalise_phone("6361222162") == "+916361222162"
    assert auth.normalise_phone("+91 63612 22162") == "+916361222162"
    assert auth.normalise_phone("916361222162") == "+916361222162"
    assert auth.normalise_phone("06361222162") == "+916361222162"


def test_otp_hash_verify():
    code = auth.generate_otp()
    h = auth.hash_otp(code)
    assert auth.verify_otp_hash(code, h)
    assert not auth.verify_otp_hash("000000", h) or code == "000000"


def test_session_roundtrip():
    tok = auth.make_session(42)
    assert auth.read_session(tok) == 42
    assert auth.read_session("garbage") is None
    assert auth.read_session(None) is None


def test_session_tamper_rejected():
    tok = auth.make_session(1)
    assert auth.read_session(tok[:-2] + "xx") is None


def test_session_survives_mac_containing_separator():
    """Regression: a raw 32-byte MAC contains 0x2E ~12% of the time.

    The old format embedded the MAC raw and split on b'.', so ~1 in 9 logins
    silently bounced the user back to the login page. Encode both parts.
    """
    for uid in range(2000):
        assert auth.read_session(auth.make_session(uid)) == uid


def test_payments_simulate_mode():
    assert not payments.live()
    o = payments.create_order(2499.0, "ORD-TEST")
    assert o["provider"] == "simulate" and o["amount"] == 249900
    assert payments.verify_signature("a", "b", "anything") is True   # simulate passes


def test_dev_otp_disabled_when_whatsapp_configured(monkeypatch):
    """An exposed OTP lets anyone take over an account — must be off in prod."""
    from app import notify
    monkeypatch.delenv("DEV_OTP", raising=False)
    monkeypatch.delenv("WA_BRIDGE_URL", raising=False)
    monkeypatch.setenv("WA_TOKEN", "EAAGtest")
    monkeypatch.setenv("WA_PHONE_ID", "123456")
    assert notify.dev_otp_enabled() is False
    # explicit override wins
    monkeypatch.setenv("DEV_OTP", "1")
    assert notify.dev_otp_enabled() is True
    monkeypatch.setenv("DEV_OTP", "0")
    assert notify.dev_otp_enabled() is False


def test_dev_otp_on_with_no_channel(monkeypatch):
    from app import notify
    monkeypatch.delenv("DEV_OTP", raising=False)
    monkeypatch.delenv("WA_BRIDGE_URL", raising=False)
    monkeypatch.delenv("WA_TOKEN", raising=False)
    monkeypatch.delenv("WA_PHONE_ID", raising=False)
    assert notify.dev_otp_enabled() is True


def test_whatsapp_falls_back_to_simulated(client):
    from app.database import SessionLocal
    db = SessionLocal()
    res = notify.send_whatsapp(db, "+916361222162", "hello", kind="test")
    assert res["status"] in ("sent", "simulated", "failed")
    # a notification row must always be written
    from app import models
    assert db.query(models.Notification).count() >= 1
    db.close()
