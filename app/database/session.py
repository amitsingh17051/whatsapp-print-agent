"""Database engine and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# SQLite connect_args for multithreading if needed
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def init_db() -> None:
    """Initialize database tables and ensure column migrations."""
    import app.models.print_job  # noqa: F401
    from app.database.base import Base
    Base.metadata.create_all(bind=engine)

    # Safe lightweight schema migration for SQLite
    if settings.DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            from sqlalchemy import text
            from sqlalchemy.exc import OperationalError
            for col, col_type in [
                ("gateway_order_id", "VARCHAR(100)"),
                ("gateway_payment_id", "VARCHAR(100)"),
                ("payment_link_url", "VARCHAR(500)"),
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE payments ADD COLUMN {col} {col_type}"))
                    conn.commit()
                except OperationalError:
                    # Column already exists
                    continue


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
