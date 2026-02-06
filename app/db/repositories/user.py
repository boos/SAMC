"""
User repository.

Handles database operations for User model.
"""

from typing import Optional

from sqlmodel import Session, select

from app.models.user import User


class UserRepository:
    """Repository for User database operations."""

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLModel database session
        """
        self.session = session

    def create(self, user: User) -> User:
        """
        Create a new user in the database.

        Args:
            user: User instance to create

        Returns:
            Created user with generated id
        """
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User instance if found, None otherwise
        """
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User email

        Returns:
            User instance if found, None otherwise
        """
        statement = select(User).where(User.email == email)
        return self.session.exec(statement).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """
        Get all users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of users
        """
        statement = select(User).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def update(self, user: User) -> User:
        """
        Update an existing user.

        Args:
            user: User instance with updated data

        Returns:
            Updated user
        """
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def delete(self, user_id: int) -> bool:
        """
        Delete a user by ID.

        Args:
            user_id: User ID to delete

        Returns:
            True if deleted, False if not found
        """
        user = self.get_by_id(user_id)
        if user:
            self.session.delete(user)
            self.session.commit()
            return True
        return False

    def exists_by_email(self, email: str) -> bool:
        """
        Check if a user with the given email exists.

        Args:
            email: Email to check

        Returns:
            True if user exists, False otherwise
        """
        return self.get_by_email(email) is not None
