"""Users router providing authenticated user profile and location management."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserLocationResponse, UserLocationUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.patch(
    "/me/location",
    response_model=UserLocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user location snapshot",
    description="Update the authenticated user's current point-in-time geographic coordinates. Continuous tracking is not performed.",
    responses={
        200: {"description": "User location snapshot successfully updated."},
        401: {"description": "Authentication required. Bearer token missing or invalid."},
        422: {"description": "Validation error for coordinate boundaries."},
    },
)
def update_user_location(
    location_in: UserLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserLocationResponse:
    """Update authenticated user's point-in-time latitude and longitude."""
    now = datetime.now(timezone.utc)
    current_user.latitude = location_in.latitude
    current_user.longitude = location_in.longitude
    current_user.location_updated_at = now

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return UserLocationResponse(
        latitude=current_user.latitude,
        longitude=current_user.longitude,
        location_updated_at=current_user.location_updated_at,
    )
