from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from app.core.settings import settings
from app.db.schema import Base

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Automatically verifies connection health
    pool_size=5,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# For FastAPI dependency injection
def get_db():
    db = SessionLocal()
    try:
        yield db
    # NOTE: FastAPI's background middleware handles rollback on failure
    finally:
        db.close()

# For non-request scripts
@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
