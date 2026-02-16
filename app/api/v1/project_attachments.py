"""
Project Attachments API endpoints.

Handles file uploads, listing, and deletion for project attachments.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Path
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.project_attachment import ProjectAttachment
from app.schemas.project_attachment import (
    ProjectAttachmentResponse,
    ProjectAttachmentListResponse,
    ProjectAttachmentUpdate
)
from app.services.storage_service import get_storage_service, StorageService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/projects/{project_id}/attachments", tags=["project-attachments"])

# Maximum attachments per project
MAX_ATTACHMENTS_PER_PROJECT = 20


def get_project_or_404(project_id: UUID, db: Session, current_user: User) -> Project:
    """Get project by ID or raise 404. Also checks user has access."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.company_id == current_user.company_id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project


@router.post("", response_model=ProjectAttachmentResponse, status_code=201)
async def upload_attachment(
    project_id: UUID = Path(..., description="Project ID"),
    file: UploadFile = File(..., description="File to upload (image or PDF)"),
    description: Optional[str] = Query(None, max_length=1000, description="Optional description"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service)
):
    """
    Upload an attachment to a project.
    
    Supported formats:
    - Images: JPEG, PNG, WebP, GIF
    - Documents: PDF
    
    Maximum size: 10MB
    Maximum attachments per project: 20
    """
    # Verify project exists and user has access
    project = get_project_or_404(project_id, db, current_user)
    
    # Check attachment count limit
    current_count = db.query(ProjectAttachment).filter(
        ProjectAttachment.project_id == project_id
    ).count()
    
    if current_count >= MAX_ATTACHMENTS_PER_PROJECT:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum attachments ({MAX_ATTACHMENTS_PER_PROJECT}) reached for this project"
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
            folder="attachments",
            validate_images_only=False  # Allow PDFs too
        )
        
        # Create database record
        attachment = ProjectAttachment(
            filename=file.filename or 'attachment',
            file_url=file_url,
            file_type=content_type,
            file_size=file_size,
            description=description,
            project_id=project_id,
            uploaded_by_user_id=current_user.id
        )
        
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
        
        logger.info(f"Attachment uploaded: {attachment.id} for project {project_id}")
        
        # Build response with user info
        response = ProjectAttachmentResponse.model_validate(attachment)
        response.uploaded_by_name = current_user.name
        
        return response
        
    except ValueError as e:
        logger.warning(f"Attachment upload validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Attachment upload failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to upload attachment")


@router.get("", response_model=ProjectAttachmentListResponse)
async def list_attachments(
    project_id: UUID = Path(..., description="Project ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all attachments for a project.
    
    Returns attachments ordered by creation date (newest first).
    """
    # Verify project exists and user has access
    get_project_or_404(project_id, db, current_user)
    
    # Get attachments with user info
    attachments = db.query(ProjectAttachment).filter(
        ProjectAttachment.project_id == project_id
    ).order_by(ProjectAttachment.created_at.desc()).all()
    
    # Build response with user names
    attachment_responses = []
    for attachment in attachments:
        response = ProjectAttachmentResponse.model_validate(attachment)
        if attachment.uploaded_by:
            response.uploaded_by_name = attachment.uploaded_by.name
        attachment_responses.append(response)
    
    return ProjectAttachmentListResponse(
        attachments=attachment_responses,
        total=len(attachment_responses),
        max_allowed=MAX_ATTACHMENTS_PER_PROJECT
    )


@router.delete("/{attachment_id}", status_code=204)
async def delete_attachment(
    project_id: UUID = Path(..., description="Project ID"),
    attachment_id: UUID = Path(..., description="Attachment ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service)
):
    """
    Delete an attachment from a project.
    
    Removes both the database record and the file from storage.
    """
    # Verify project exists and user has access
    get_project_or_404(project_id, db, current_user)
    
    # Get attachment
    attachment = db.query(ProjectAttachment).filter(
        ProjectAttachment.id == attachment_id,
        ProjectAttachment.project_id == project_id
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
        
        logger.info(f"Attachment deleted: {attachment_id} from project {project_id}")
        
    except Exception as e:
        logger.error(f"Failed to delete attachment: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete attachment")


@router.put("/{attachment_id}", response_model=ProjectAttachmentResponse)
async def update_attachment(
    project_id: UUID = Path(..., description="Project ID"),
    attachment_id: UUID = Path(..., description="Attachment ID"),
    update_data: ProjectAttachmentUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update attachment description.
    
    Only the description field can be updated.
    """
    # Verify project exists and user has access
    get_project_or_404(project_id, db, current_user)
    
    # Get attachment
    attachment = db.query(ProjectAttachment).filter(
        ProjectAttachment.id == attachment_id,
        ProjectAttachment.project_id == project_id
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
        response = ProjectAttachmentResponse.model_validate(attachment)
        if attachment.uploaded_by:
            response.uploaded_by_name = attachment.uploaded_by.name
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to update attachment: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update attachment")
