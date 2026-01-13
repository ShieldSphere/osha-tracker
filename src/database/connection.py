import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from src.config import settings
from src.database.models import Base


# Adjust connection string for pg8000 driver if needed
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://") and "postgresql+pg8000://" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+pg8000://", 1)

# Serverless-optimized settings
is_serverless = os.environ.get("VERCEL") == "1"
engine = create_engine(
    db_url,
    pool_pre_ping=True,
    pool_size=1 if is_serverless else 5,
    max_overflow=0 if is_serverless else 10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database session (for non-FastAPI use)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
