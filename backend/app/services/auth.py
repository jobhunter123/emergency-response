"""Authentication service implementing core business and database operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


class EmailAlreadyExistsError(Exception):
    """Raised when attempting to create a user with an email already in use."""

    pass


def normalize_email(email: str) -> str:
    """Normalize email address to lowercase and strip surrounding whitespace."""
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Retrieve a user from database by email address."""
    normalized = normalize_email(email)
    statement = select(User).where(User.email == normalized)
    return db.scalars(statement).first()


def get_user_by_id(db: Session, user_id: str) -> User | None:
    """Retrieve a user from database by primary key UUID string."""
    return db.get(User, user_id)


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Verify user credentials and return the User instance if valid, or None."""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(db: Session, user_data: UserCreate) -> User:
    """Create and persist a new User in the database with a hashed password."""
    normalized_email = normalize_email(user_data.email)
    existing_user = get_user_by_email(db, normalized_email)
    if existing_user is not None:
        raise EmailAlreadyExistsError("A user with this email already exists")

    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=normalized_email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_access_token_for_user(user: User) -> str:
    """Generate a signed JWT access token for a given user entity."""
    return create_access_token(subject=user.id)
