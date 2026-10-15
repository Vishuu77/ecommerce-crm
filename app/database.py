"""Database setup — SQLAlchemy + SQLite (local, zero-config).

Set DATABASE_URL to point at Postgres/Supabase for cloud, e.g.
    postgresql+psycopg://user:pass@host:5432/db
"""
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "crm.db"),
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_ADDED_COLUMNS = {
    "products": {
        "mrp": "FLOAT DEFAULT 0",
        "rating": "FLOAT DEFAULT 0",
        "review_count": "INTEGER DEFAULT 0",
    },
}


def _add_missing_columns():
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            if table not in insp.get_table_names():
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def init_db():
    from app import models  # noqa: F401  (register tables)
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
