"""Database initialization utilities."""

from sqlalchemy import Engine

from app.db.base import Base
from app.db.session import engine as default_engine
import app.models  # noqa: F401 - ensures all models are imported and registered with Base.metadata


def init_db(engine: Engine | None = None) -> None:
    """Create all database tables registered with SQLAlchemy declarative base.

    Args:
        engine: Optional SQLAlchemy Engine. If omitted, the default engine
            from app.db.session is used.
    """
    target_engine = engine or default_engine
    Base.metadata.create_all(bind=target_engine)

    # Ensure schema backward-compatibility for SQLite if photo_url was added
    try:
        from sqlalchemy import text
        with target_engine.connect() as conn:
            columns = conn.execute(text("PRAGMA table_info(emergency_reports)")).fetchall()
            col_names = [col[1] for col in columns]
            if col_names and "photo_url" not in col_names:
                conn.execute(text("ALTER TABLE emergency_reports ADD COLUMN photo_url VARCHAR(512)"))
                conn.commit()
    except Exception:
        # Non-fatal if table not yet created or underlying engine is non-SQLite
        pass
