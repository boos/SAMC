"""
FastAPI application factory.

Creates and configures the FastAPI application instance.
"""

from fastapi import FastAPI

from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Structured Adaptive Multi-Cycle Training Periodization.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json")

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "message": "SAMC API",
        "version": settings.VERSION,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthyS",
        "service": "samc-api",
        "version": settings.VERSION
    }


@app.get("/info")
async def info():
    return {
        "project name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "authors": settings.AUTHORS,
        "authors emails": settings.AUTHORS_EMAILS,
        "project url": settings.PROJECT_URL
    }

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

@app.get("/items/")
async def read_items(token: str = Depends(oauth2_scheme)):
    return {"token": token}
