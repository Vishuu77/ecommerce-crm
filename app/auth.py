"""Auth: password hashing, OTP, and signed session cookies (stdlib only).

Kept dependency-free (hashlib/hmac/secrets) so it installs cleanly on Windows
and any host — no bcrypt/itsdangerous build steps.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import os
import secrets
import time

from datetime import datetime, timedelta

SECRET = os.environ.get("APP_SECRET", "dev-secret-change-me-in-production")
OTP_TTL_SECONDS = 300          # 5 minutes
OTP_MAX_ATTEMPTS = 5
SESSION_TTL_SECONDS = 60 * 60 * 24 * 14   # 14 days
PBKDF2_ROUNDS = 200_000


# ---------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


# ---------------------------------------------------------------- OTP
def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(code: str) -> str:
    return hmac.new(SECRET.encode(), code.encode(), hashlib.sha256).hexdigest()


def verify_otp_hash(code: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(code), stored_hash)


def otp_expiry() -> datetime:
    return datetime.utcnow() + timedelta(seconds=OTP_TTL_SECONDS)


# ---------------------------------------------------------------- sessions
def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(txt: str) -> bytes:
    return base64.urlsafe_b64decode(txt + "=" * (-len(txt) % 4))


def _sign(payload: bytes) -> str:
    """Sign a payload as '<b64url(payload)>.<b64url(hmac)>'.

    Each part is base64url-encoded *separately*: a raw MAC is 32 random bytes
    and ~12% of them contain 0x2E ('.'), which would collide with the separator
    and break ~1 in 9 sessions.
    """
    mac = hmac.new(SECRET.encode(), payload, hashlib.sha256).digest()
    return f"{_b64e(payload)}.{_b64e(mac)}"


def make_session(user_id: int) -> str:
    exp = int(time.time()) + SESSION_TTL_SECONDS
    return _sign(f"{user_id}:{exp}".encode())


def read_session(token: str | None) -> int | None:
    if not token:
        return None
    try:
        payload_b64, mac_b64 = token.split(".")
        payload, mac = _b64d(payload_b64), _b64d(mac_b64)
        expected = hmac.new(SECRET.encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected):
            return None
        uid, exp = payload.decode().split(":")
        if int(exp) < time.time():
            return None
        return int(uid)
    except Exception:
        return None


# ---------------------------------------------------------------- pending
# Carries the just-registered user from /register to /verify. Looked up by
# phone alone, two accounts sharing a number would collide and the OTP would
# verify (and log in) the wrong user.
PENDING_TTL_SECONDS = 900


def make_pending(user_id: int) -> str:
    exp = int(time.time()) + PENDING_TTL_SECONDS
    return _sign(f"pending:{user_id}:{exp}".encode())


def read_pending(token: str | None) -> int | None:
    if not token:
        return None
    try:
        payload_b64, mac_b64 = token.split(".")
        payload, mac = _b64d(payload_b64), _b64d(mac_b64)
        expected = hmac.new(SECRET.encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected):
            return None
        kind, uid, exp = payload.decode().split(":")
        if kind != "pending" or int(exp) < time.time():
            return None
        return int(uid)
    except Exception:
        return None


# ---------------------------------------------------------------- phone
def normalise_phone(raw: str) -> str:
    """Normalise an Indian phone number to E.164 (+91XXXXXXXXXX)."""
    digits = "".join(ch for ch in (raw or "") if ch.isdigit())
    if len(digits) == 10:
        return "+91" + digits
    if digits.startswith("91") and len(digits) == 12:
        return "+" + digits
    if digits.startswith("0") and len(digits) == 11:
        return "+91" + digits[1:]
    return "+" + digits if digits else ""
