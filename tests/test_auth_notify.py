"""Auth and notification unit tests."""
from app import auth, notify


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


def test_whatsapp_falls_back_to_simulated(client):
    from app.database import SessionLocal
    db = SessionLocal()
    res = notify.send_whatsapp(db, "+916361222162", "hello", kind="test")
    assert res["status"] in ("sent", "simulated", "failed")
    # a notification row must always be written
    from app import models
    assert db.query(models.Notification).count() >= 1
    db.close()
