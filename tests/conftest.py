"""Pytest fixtures — isolated in-memory DB per test session."""
import os
import pytest
from fastapi.testclient import TestClient

# force a throwaway SQLite file before the app imports its engine
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "_test.db")

from app.main import app                      # noqa: E402
from app.database import init_db, SessionLocal  # noqa: E402
from app import seed                          # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    init_db()
    db = SessionLocal()
    try:
        seed.seed(db)
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        from app import models
        for m in (models.Ticket, models.Order, models.Product):
            db.query(m).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
