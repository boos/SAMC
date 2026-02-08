"""
API v1 router.

Aggregates all v1 endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import analytics, auth, physio, sports, training

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    auth.router, prefix="/auth", tags=["Authentication"]
)
api_router.include_router(
    physio.router, prefix="/physio", tags=["Physiological data"]
)
api_router.include_router(
    training.router,
    prefix="/training/sessions",
    tags=["Training sessions"],
)
api_router.include_router(
    sports.router, prefix="/sports", tags=["Sports configuration"]
)
api_router.include_router(
    analytics.router, prefix="/analytics", tags=["Analytics"]
)
