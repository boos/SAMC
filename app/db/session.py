"""
Database session management.

Provides SQLModel engine and session creation.
"""

from sqlmodel import create_engine, Session
from typing import Generator

from app.core.config import settings

# Create database engine
DATABASE_URL: str = (f"postgresql://{settings.DATABASE_USER}:{settings.DATABASE_PASSWORD}@{settings.DATABASE_HOST}"
                     f":{settings.DATABASE_PORT}"
                     f"/{settings.DATABASE_DBNAME}")

engine = create_engine(
    DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    pool_pre_ping=True,   # Verify connections before using
    pool_size=5,          # Connection pool size
    max_overflow=10       # Max connections beyond pool_size
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI endpoints to get database session.
    
    Yields:
        SQLModel Session instance
    
    Example:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    with Session(engine) as session:
        yield session
