from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session, joinedload

from app.repositories.base import BaseRepository
from app.models.notification import NotificationSettings, NotificationRecipient
from app.schemas.notification import (
    NotificationSettingsCreate,
    NotificationSettingsUpdate,
    NotificationRecipientCreate,
)


class NotificationRepository(BaseRepository[NotificationSettings]):
    """Repository for notification operations."""
    
    def __init__(self, db: Session):
        super().__init__(NotificationSettings, db)
    
    def get_by_company(self, company_id: UUID) -> Optional[NotificationSettings]:
        """Get notification settings by company ID."""
        return self.db.query(NotificationSettings).filter(
            NotificationSettings.company_id == company_id
        ).options(
            joinedload(NotificationSettings.recipients)
        ).first()
    
    def create_settings(self, company_id: UUID, obj_in: NotificationSettingsCreate) -> NotificationSettings:
        """Create notification settings for a company."""
        db_obj = NotificationSettings(
            company_id=company_id,
            enabled=obj_in.enabled
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def update_settings(self, settings_id: UUID, obj_in: NotificationSettingsUpdate) -> Optional[NotificationSettings]:
        """Update notification settings."""
        db_obj = self.get_by_id(settings_id)
        if not db_obj:
            return None
        
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    # Recipient methods
    def add_recipient(self, settings_id: UUID, recipient_in: NotificationRecipientCreate) -> NotificationRecipient:
        """Add a recipient to notification settings."""
        db_obj = NotificationRecipient(
            notification_setting_id=settings_id,
            email=recipient_in.email,
            name=recipient_in.name,
            is_active=True
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def remove_recipient(self, recipient_id: UUID) -> bool:
        """Remove a recipient."""
        db_obj = self.db.query(NotificationRecipient).filter(
            NotificationRecipient.id == recipient_id
        ).first()
        
        if db_obj:
            self.db.delete(db_obj)
            self.db.commit()
            return True
        return False
    
    def get_recipient(self, recipient_id: UUID) -> Optional[NotificationRecipient]:
        """Get a recipient by ID."""
        return self.db.query(NotificationRecipient).filter(
            NotificationRecipient.id == recipient_id
        ).first()
    
    def list_recipients(self, settings_id: UUID, active_only: bool = True) -> List[NotificationRecipient]:
        """List all recipients for a notification setting."""
        query = self.db.query(NotificationRecipient).filter(
            NotificationRecipient.notification_setting_id == settings_id
        )
        
        if active_only:
            query = query.filter(NotificationRecipient.is_active == True)
        
        return query.all()
    
    def get_active_recipient_emails(self, company_id: UUID) -> List[str]:
        """Get list of active recipient emails for a company."""
        settings = self.get_by_company(company_id)
        
        if not settings or not settings.enabled:
            return []
        
        recipients = self.db.query(NotificationRecipient).filter(
            NotificationRecipient.notification_setting_id == settings.id,
            NotificationRecipient.is_active == True
        ).all()
        
        return [recipient.email for recipient in recipients]
