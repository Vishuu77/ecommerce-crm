"""Pytest fixtures — isolated throwaway SQLite DB, rebuilt fresh each run."""
import os
import pytest
from fastapi.testclient import TestClient

_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test.db")

# force a throwaway SQLite file before the app imports its engine
os.environ["DATABASE_URL"] = "sqlite:///" + _DB

from app.main import app                        # noqa: E402
from app.database import init_db, SessionLocal, engine  # noqa: E402
from app import seed, models                    # noqa: E402

# every table, so no state survives a run (User/CartItem included)
_TABLES = (models.CartItem, models.OrderItem, models.Notification,
           models.Ticket, models.Order, models.User, models.Product)


def _wipe(db):
    for m in _TABLES:
        db.query(m).delete()
    db.commit()


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    # start from a clean file — a stale _test.db leaks users across runs and
    # makes registration return 200 instead of 303
    if os.path.exists(_DB):
        os.remove(_DB)
    init_db()
    db = SessionLocal()
    try:
        seed.seed(db)
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        _wipe(db)
    finally:
        db.close()
    engine.dispose()          # release the file handle before deleting (Windows)
    if os.path.exists(_DB):
        os.remove(_DB)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
