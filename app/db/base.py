"""
Base database configuration.

Import all models here so Alembic can detect them for migrations.
"""

from sqlmodel import SQLModel

# Import all models for Alembic autogenerate
from app.models.user import User  # noqa: F401
# Week 2: from app.models.physio_data import PhysioData
# Week 3: from app.models.training_session import TrainingSession
# Week 4: from app.models.daily_state import DailyState
