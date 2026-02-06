"""
API v1 router.

Aggregates all v1 endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, physio

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(physio.router, prefix="/physio", tags=["Physio Data"])
