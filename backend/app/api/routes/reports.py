import os
from pathlib import Path
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.emergency_report import (
    EmergencyReportCreate,
    EmergencyReportResponse,
    EmergencyReportSubmissionResponse,
    IncidentSummary,
)
from app.services.confidence import get_confidence_level
from app.services.emergency_report import (
    create_emergency_report,
    get_report_by_id,
)

router = APIRouter(prefix="/reports", tags=["Emergency Reports"])

MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_PHOTO_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads" / "report_photos"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "",
    response_model=EmergencyReportSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an emergency report",
    description="Submit a localized emergency observation. Clusters with nearby matching incidents if found, or creates a new incident. Optionally accepts photo evidence.",
    responses={
        201: {"description": "Emergency report created and grouped successfully."},
        400: {"description": "Invalid file format or upload."},
        401: {"description": "Authentication required. Bearer token missing or invalid."},
        413: {"description": "Photo size exceeds 5MB limit."},
        422: {"description": "Validation error. Coordinates or fields out of bounds."},
    },
)
async def submit_report(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmergencyReportSubmissionResponse:
    """Submit an emergency observation with optional photo evidence for incident aggregation."""
    content_type = request.headers.get("content-type", "")
    photo_url: str | None = None

    if content_type.startswith("multipart/form-data") or content_type.startswith(
        "application/x-www-form-urlencoded"
    ):
        form = await request.form()
        try:
            report_data_dict = {
                "emergency_type": form.get("emergency_type"),
                "description": form.get("description"),
                "severity": form.get("severity"),
                "latitude": form.get("latitude"),
                "longitude": form.get("longitude"),
            }
            report_in = EmergencyReportCreate(**report_data_dict)
        except ValidationError as val_err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=val_err.errors(),
            ) from val_err
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        # Process optional photo upload
        photo_field = form.get("photo")
        if photo_field is not None and hasattr(photo_field, "filename") and photo_field.filename:
            content_type_photo = getattr(photo_field, "content_type", "").lower()
            if content_type_photo not in ALLOWED_PHOTO_MIME_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid image type '{content_type_photo}'. Supported formats: JPEG, PNG, WebP.",
                )

            content = await photo_field.read()
            if len(content) > MAX_PHOTO_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Photo size exceeds maximum allowed limit of 5MB.",
                )

            ext = ALLOWED_PHOTO_MIME_TYPES[content_type_photo]
            safe_filename = f"{uuid.uuid4().hex}{ext}"
            file_dest = UPLOAD_DIR / safe_filename
            with open(file_dest, "wb") as f:
                f.write(content)

            photo_url = f"/uploads/report_photos/{safe_filename}"
    else:
        # Standard JSON request body
        try:
            json_body = await request.json()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid JSON payload.",
            ) from exc

        try:
            report_in = EmergencyReportCreate.model_validate(json_body)
        except ValidationError as val_err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=val_err.errors(),
            ) from val_err

    report, incident = create_emergency_report(
        db=db,
        user=current_user,
        report_data=report_in,
        photo_url=photo_url,
    )
    incident_summary_data = IncidentSummary.model_validate(incident).model_dump()
    incident_summary_data["confidence_level"] = get_confidence_level(
        incident.confidence_score
    )

    return EmergencyReportSubmissionResponse(
        report=EmergencyReportResponse.model_validate(report),
        incident=IncidentSummary(**incident_summary_data),
    )


@router.get(
    "/{report_id}",
    response_model=EmergencyReportResponse,
    summary="Retrieve an emergency report",
    description="Fetch details of a submitted emergency report. Accessible by the author or registered responders.",
    responses={
        200: {"description": "Report details retrieved."},
        401: {"description": "Authentication required."},
        403: {"description": "Forbidden. User is not the owner or a responder."},
        404: {"description": "Report not found."},
    },
)
def read_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmergencyReportResponse:
    """Retrieve report by ID if owned by current user or requested by responder."""
    report = get_report_by_id(db=db, report_id=report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency report not found",
        )

    # Permission check: must be owner or responder
    if report.user_id != current_user.id and not current_user.is_responder:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this emergency report",
        )

    return EmergencyReportResponse.model_validate(report)
