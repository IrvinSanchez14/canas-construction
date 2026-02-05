from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import (
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    NotificationSettingsCreate,
    NotificationRecipientCreate,
    NotificationRecipientResponse
)

router = APIRouter(prefix="/notification-settings", tags=["Notifications"])


@router.get("", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get notification settings for the user's company."""
    repo = NotificationRepository(db)
    settings = repo.get_by_company(current_user.company_id)
    
    if not settings:
        # Auto-create settings if they don't exist
        settings = repo.create_settings(
            current_user.company_id,
            NotificationSettingsCreate(company_id=current_user.company_id, enabled=True)
        )
    
    return settings


@router.patch("", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    settings_update: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update notification settings (admin only)."""
    # TODO: Add admin role check when role-based auth is implemented
    repo = NotificationRepository(db)
    settings = repo.get_by_company(current_user.company_id)
    
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification settings not found"
        )
    
    updated = repo.update_settings(settings.id, settings_update)
    return updated


@router.post("/recipients", response_model=NotificationRecipientResponse, status_code=status.HTTP_201_CREATED)
async def add_recipient(
    recipient: NotificationRecipientCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a notification recipient (admin only)."""
    # TODO: Add admin role check when role-based auth is implemented
    repo = NotificationRepository(db)
    settings = repo.get_by_company(current_user.company_id)
    
    if not settings:
        # Auto-create settings if they don't exist
        settings = repo.create_settings(
            current_user.company_id,
            NotificationSettingsCreate(company_id=current_user.company_id, enabled=True)
        )
    
    new_recipient = repo.add_recipient(settings.id, recipient)
    return new_recipient


@router.get("/recipients", response_model=List[NotificationRecipientResponse])
async def list_recipients(
    active_only: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all notification recipients."""
    repo = NotificationRepository(db)
    settings = repo.get_by_company(current_user.company_id)
    
    if not settings:
        return []
    
    recipients = repo.list_recipients(settings.id, active_only=active_only)
    return recipients


@router.delete("/recipients/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_recipient(
    recipient_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove a notification recipient (admin only)."""
    # TODO: Add admin role check when role-based auth is implemented
    repo = NotificationRepository(db)
    
    # Verify recipient belongs to user's company
    recipient = repo.get_recipient(recipient_id)
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient not found"
        )
    
    settings = repo.get_by_company(current_user.company_id)
    if not settings or recipient.notification_setting_id != settings.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot remove recipient from another company"
        )
    
    success = repo.remove_recipient(recipient_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient not found"
        )
