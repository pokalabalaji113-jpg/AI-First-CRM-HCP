"""SQLAlchemy engine / session setup for PostgreSQL."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db() -> None:
    """Create tables if they don't exist (called on startup)."""
    # Import models so they are registered on the Base metadata.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
