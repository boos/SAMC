"""
Base database configuration.

Import all models here so Alembic can detect them for migrations.
"""

# Import all models for Alembic autogenerate
from app.models.user import User  # noqa: F401
from app.models.physio import PhysioData  # noqa: F401
from app.models.training_session import TrainingSession  # noqa: F401
from app.models.user_sport_config import UserSportConfig  # noqa: F401
from app.models.micro_cycle import MicroCycleConfig  # noqa: F401
