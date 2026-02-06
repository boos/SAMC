"""
Database initialization.

Creates all tables and enables TimescaleDB hypertables.
"""

# TODO: check if it works


from sqlmodel import SQLModel, text

from app.core.config import settings
from app.db.session import engine


def init_db() -> None:
    """
    Initialize database schema.
    
    - Creates all SQLModel tables
    - Enables TimescaleDB extension (if configured)
    - Creates TimescaleDB hypertables for time-series data
    """

    # Import all models so SQLModel.metadata has them
    from app.models.user import User  # noqa: F401
    # Week 2: from app.models.physio_data import PhysioData
    # Week 3: from app.models.training_session import TrainingSession
    # Week 4: from app.models.daily_state import DailyState

    print("Creating database tables...")
    SQLModel.metadata.create_all(engine)
    print("✓ Tables created successfully")

    if settings.TIMESCALEDB_ENABLED:
        print("Enabling TimescaleDB extension...")
        try:
            with engine.connect() as conn:
                # Enable TimescaleDB extension
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
                conn.commit()
                print("✓ TimescaleDB extension enabled")

                # Week 2: Convert physio_data to hypertable  # conn.execute(text(  #     "SELECT create_hypertable('physio_data', 'date', "  #     "if_not_exists => TRUE);"  # ))  # print("✓ physio_data converted to hypertable")

        except Exception as e:
            print(f"⚠ TimescaleDB setup failed: {e}")
            print("  Continuing without TimescaleDB features...")

    print("Database initialization complete!")


if __name__ == "__main__":
    init_db()
