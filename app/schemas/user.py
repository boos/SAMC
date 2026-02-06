"""
User API schemas.

Pydantic models for user-related request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# Shared properties
class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    full_name: Optional[str]


# Request schemas
class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field("Password", min_length=8, description="Password (min 8 characters)")


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    email: Optional[EmailStr]
    full_name: Optional[str]
    password: Optional[str] = Field(None, min_length=8, description="Password (min 8 characters)")


# Response schemas
class UserResponse(UserBase):
    """Schema for user data in API responses (no sensitive data)."""
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Allows creation from SQLModel objects
