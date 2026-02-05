from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class NotificationSettings(BaseModel):
    """Notification settings per company."""
    
    __tablename__ = "notification_settings"
    
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True)
    enabled = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="notification_settings")
    recipients = relationship("NotificationRecipient", back_populates="settings", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<NotificationSettings(company_id={self.company_id}, enabled={self.enabled})>"


class NotificationRecipient(BaseModel):
    """Email recipients for notifications."""
    
    __tablename__ = "notification_recipients"
    
    notification_setting_id = Column(UUID(as_uuid=True), ForeignKey("notification_settings.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    settings = relationship("NotificationSettings", back_populates="recipients")
    
    def __repr__(self):
        return f"<NotificationRecipient(email={self.email}, is_active={self.is_active})>"
