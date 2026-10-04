"""Alerts router providing alert retrieval and status updates for authenticated users."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.alert import AlertResponse
from app.services.alerts import (
    AlertForbiddenError,
    AlertNotFoundError,
    get_user_alerts,
    mark_alert_as_read,
)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get(
    "",
    response_model=list[AlertResponse],
    summary="List user alerts",
    description="Retrieve emergency alerts targeted to the current authenticated user, sorted newest first.",
    responses={
        200: {"description": "List of emergency alerts for the authenticated user."},
        401: {"description": "Authentication required. Bearer token missing or invalid."},
    },
)
def list_alerts(
    unread_only: bool = Query(
        default=False,
        description="Filter to return only unread alerts",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AlertResponse]:
    """Retrieve personal emergency alerts for the logged-in user."""
    alerts = get_user_alerts(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
    )
    return [AlertResponse.model_validate(a) for a in alerts]


@router.patch(
    "/{alert_id}/read",
    response_model=AlertResponse,
    summary="Mark alert as read",
    description="Mark an emergency alert belonging to the authenticated user as read, recording the read timestamp.",
    responses={
        200: {"description": "Alert successfully marked as read."},
        401: {"description": "Authentication required. Bearer token missing or invalid."},
        403: {"description": "Forbidden. User is not the owner of this alert."},
        404: {"description": "Alert not found."},
    },
)
def mark_read(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertResponse:
    """Mark an alert as read by the recipient user."""
    try:
        updated_alert = mark_alert_as_read(
            db=db,
            alert_id=alert_id,
            current_user=current_user,
        )
    except AlertNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        ) from exc
    except AlertForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return AlertResponse.model_validate(updated_alert)
