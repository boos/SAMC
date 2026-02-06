"""
User service.

Business logic for user management and authentication.
"""

from datetime import timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.repositories.user import UserRepository
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserLogin


class UserService:
    """Service for user-related business logic."""

    def __init__(self, session: Session):
        """
        Initialize service with database session.

        Args:
            session: SQLModel database session
        """
        self.repository = UserRepository(session)

    def register(self, user_data: UserCreate) -> User:
        """
        Register a new user.

        Args:
            user_data: User registration data

        Returns:
            Created user

        Raises:
            HTTPException: If email already exists
        """
        # Check if user already exists
        if self.repository.exists_by_email(user_data.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already registered")

        # Create user with hashed password
        user = User(email=user_data.email, hashed_password=get_password_hash(user_data.password),
                    full_name=user_data.full_name, )

        return self.repository.create(user)

    def authenticate(self, login_data: UserLogin) -> Token:
        """
        Authenticate user and return access token.

        Args:
            login_data: User login credentials

        Returns:
            JWT access token

        Raises:
            HTTPException: If credentials are invalid
        """
        # Get user by email
        user = self.repository.get_by_email(login_data.email)

        # Verify user exists and password is correct
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password",
                                headers={ "WWW-Authenticate": "Bearer" }, )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={ "sub": user.email }, expires_delta=access_token_expires)

        print(access_token)

        return Token(access_token=access_token, token_type="bearer")

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        return self.repository.get_by_email(email)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User if found, None otherwise
        """
        return self.repository.get_by_id(user_id)
