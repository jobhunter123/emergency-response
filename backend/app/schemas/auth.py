"""Pydantic schemas for authentication and JWT token responses."""

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """JWT access token response model."""

    access_token: str = Field(..., description="Encoded JWT access token")
    token_type: str = Field(default="bearer", description="Authentication scheme type")


class LoginRequest(BaseModel):
    """Credentials payload for authenticating and obtaining a JWT token."""

    email: EmailStr = Field(..., description="Registered user email address")
    password: str = Field(..., min_length=1, description="Account password")
