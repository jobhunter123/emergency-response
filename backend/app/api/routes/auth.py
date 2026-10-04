"""Authentication router defining endpoints for registration, login, and profile lookup."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import (
    EmailAlreadyExistsError,
    authenticate_user,
    create_access_token_for_user,
    create_user,
    get_user_by_email,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new citizen or responder account."""
    try:
        user = create_user(db=db, user_data=user_in)
    except EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate and receive JWT bearer token",
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
) -> Token:
    """Authenticate with email and password to receive a JWT access token."""
    user = authenticate_user(
        db=db,
        email=login_data.email,
        password=login_data.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token_for_user(user)
    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Retrieve current authenticated user",
)
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Fetch profile information for currently authenticated user."""
    return UserResponse.model_validate(current_user)
