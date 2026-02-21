"""
Visit Attachments API endpoints.

Handles file uploads, listing, and deletion for visit attachments.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Path
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.visit import Visit
from app.models.visit_attachment import VisitAttachment
from app.schemas.visit_attachment import (
    VisitAttachmentResponse,
    VisitAttachmentListResponse,
    VisitAttachmentUpdate
)
from app.services.storage_service import get_storage_service, StorageService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/visits/{visit_id}/attachments", tags=["visit-attachments"])

# Maximum attachments per visit
MAX_ATTACHMENTS_PER_VISIT = 20


def get_visit_or_404(visit_id: UUID, db: Session, current_user: User) -> Visit:
    """Get visit by ID or raise 404. Also checks user has access via project -> client -> company."""
    visit = db.query(Visit).filter(Visit.id == visit_id).first()

    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    # Multi-tenant check: visit -> project -> client -> company
    if visit.project.client.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Visit not found")

    return visit


@router.post("", response_model=VisitAttachmentResponse, status_code=201)
async def upload_attachment(
    visit_id: UUID = Path(..., description="Visit ID"),
    file: UploadFile = File(..., description="File to upload (image or PDF)"),
    description: Optional[str] = Query(None, max_length=1000, description="Optional description"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service)
):
    """
    Upload an attachment to a visit.

    Supported formats:
    - Images: JPEG, PNG, WebP, GIF
    - Documents: PDF

    Maximum size: 10MB
    Maximum attachments per visit: 20
    """
    # Verify visit exists and user has access
    visit = get_visit_or_404(visit_id, db, current_user)

    # Check attachment count limit
    current_count = db.query(VisitAttachment).filter(
        VisitAttachment.visit_id == visit_id
    ).count()

    if current_count >= MAX_ATTACHMENTS_PER_VISIT:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum attachments ({MAX_ATTACHMENTS_PER_VISIT}) reached for this visit"
        )

    # Read file content
    content = await file.read()
    file_size = len(content)
    content_type = file.content_type or 'application/octet-stream'

    try:
        # Upload to R2 storage
        file_url = await storage.upload_file(
            file_content=content,
            filename=file.filename or 'attachment',
            content_type=content_type,
            folder="visit-attachments",
            validate_images_only=False  # Allow PDFs too
        )

        # Create database record
        attachment = VisitAttachment(
            filename=file.filename or 'attachment',
            file_url=file_url,
            file_type=content_type,
            file_size=file_size,
            description=description,
            visit_id=visit_id,
            uploaded_by_user_id=current_user.id
        )

        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        logger.info(f"Attachment uploaded: {attachment.id} for visit {visit_id}")

        # Build response with user info
        response = VisitAttachmentResponse.model_validate(attachment)
        response.uploaded_by_name = current_user.full_name

        return response

    except ValueError as e:
        logger.warning(f"Attachment upload validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Attachment upload failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to upload attachment")


@router.get("", response_model=VisitAttachmentListResponse)
async def list_attachments(
    visit_id: UUID = Path(..., description="Visit ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all attachments for a visit.

    Returns attachments ordered by creation date (newest first).
    """
    # Verify visit exists and user has access
    get_visit_or_404(visit_id, db, current_user)

    # Get attachments with user info
    attachments = db.query(VisitAttachment).filter(
        VisitAttachment.visit_id == visit_id
    ).order_by(VisitAttachment.created_at.desc()).all()

    # Build response with user names
    attachment_responses = []
    for attachment in attachments:
        response = VisitAttachmentResponse.model_validate(attachment)
        if attachment.uploaded_by:
            response.uploaded_by_name = attachment.uploaded_by.full_name
        attachment_responses.append(response)

    return VisitAttachmentListResponse(
        attachments=attachment_responses,
        total=len(attachment_responses),
        max_allowed=MAX_ATTACHMENTS_PER_VISIT
    )


@router.delete("/{attachment_id}", status_code=204)
async def delete_attachment(
    visit_id: UUID = Path(..., description="Visit ID"),
    attachment_id: UUID = Path(..., description="Attachment ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service)
):
    """
    Delete an attachment from a visit.

    Removes both the database record and the file from storage.
    """
    # Verify visit exists and user has access
    get_visit_or_404(visit_id, db, current_user)

    # Get attachment
    attachment = db.query(VisitAttachment).filter(
        VisitAttachment.id == attachment_id,
        VisitAttachment.visit_id == visit_id
    ).first()

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    try:
        # Delete from storage (best effort - don't fail if file already deleted)
        try:
            await storage.delete_file(attachment.file_url)
        except Exception as e:
            logger.warning(f"Failed to delete file from storage: {e}")

        # Delete from database
        db.delete(attachment)
        db.commit()

        logger.info(f"Attachment deleted: {attachment_id} from visit {visit_id}")

    except Exception as e:
        logger.error(f"Failed to delete attachment: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete attachment")


@router.put("/{attachment_id}", response_model=VisitAttachmentResponse)
async def update_attachment(
    visit_id: UUID = Path(..., description="Visit ID"),
    attachment_id: UUID = Path(..., description="Attachment ID"),
    update_data: VisitAttachmentUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update attachment description.

    Only the description field can be updated.
    """
    # Verify visit exists and user has access
    get_visit_or_404(visit_id, db, current_user)

    # Get attachment
    attachment = db.query(VisitAttachment).filter(
        VisitAttachment.id == attachment_id,
        VisitAttachment.visit_id == visit_id
    ).first()

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    try:
        # Update description
        if update_data.description is not None:
            attachment.description = update_data.description

        db.commit()
        db.refresh(attachment)

        logger.info(f"Attachment updated: {attachment_id}")

        # Build response with user info
        response = VisitAttachmentResponse.model_validate(attachment)
        if attachment.uploaded_by:
            response.uploaded_by_name = attachment.uploaded_by.full_name

        return response

    except Exception as e:
        logger.error(f"Failed to update attachment: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update attachment")
