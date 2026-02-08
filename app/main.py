"""
FastAPI application factory.

Creates and configures the FastAPI application instance.
"""

from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer

from app.api.v1.router import api_router
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION,
              description="Structured Adaptive Multi-Cycle Training Periodization.", docs_url="/docs",
              redoc_url="/redoc", openapi_url="/openapi.json")

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/", summary="Info endpoint for monitoring.")
async def info():
    """ Project, version, authors, and project url info endpoint."""
    return { "project name": settings.PROJECT_NAME, "version": settings.VERSION, "authors": settings.AUTHORS,
             "authors emails": settings.AUTHORS_EMAILS, "project url": settings.PROJECT_URL }
