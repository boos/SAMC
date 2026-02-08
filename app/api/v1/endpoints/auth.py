"""
Authentication endpoints.

Handles user registration and login.
"""

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.db.session import get_db
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services.user_service import UserService

router = APIRouter()


@router.post("/register", summary="User registration endpoint.", response_model=UserResponse,
             status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    Args:
        user_data: User registration data (email, password, full_name)
        db: Database session

    Returns:
        Created user data (without password)

    Raises:
        HTTPException 400: If email already registered
    """
    service = UserService(db)
    user = service.register(user_data)
    return user


@router.post("/login", summary="User login endpoint via OAuth2 form (for Swagger UI).", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticate user via OAuth2 form (for Swagger UI).

    Use email as username.
    """
    service = UserService(db)
    login_data = UserLogin(email=form_data.username, password=form_data.password)
    token = service.authenticate(login_data)
    return token


@router.post("/token", summary="User login endpoint via Json.", response_model=Token)
def login_json(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user via JSON body.

    Args:
        login_data: User login credentials (email, password)
        db: Database session

    Returns:
        JWT access token
    """
    service = UserService(db)
    token = service.authenticate(login_data)
    return token
