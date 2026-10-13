"""Database connection and session configuration."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

db_url = settings.SQLALCHEMY_DATABASE_URI

# Configure SQLite-specific connection arguments if using SQLite
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing a database session to FastAPI route handlers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
