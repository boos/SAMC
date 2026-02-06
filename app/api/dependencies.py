"""
Shared API dependencies.

Reusable FastAPI dependencies for authentication and database access.
"""

from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from app.core.security import decode_access_token, oauth2_scheme
from app.db.session import get_db
from app.models.user import User
from app.services.user_service import UserService


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db), ) -> User:
    """Extract and validate the current user from the JWT token."""
    email = decode_access_token(token)
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token",
                            headers={ "WWW-Authenticate": "Bearer" }, )
    user = UserService(db).get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found",
                            headers={ "WWW-Authenticate": "Bearer" }, )
    return user
