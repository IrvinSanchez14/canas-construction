from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.email_service import EmailService
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationEvent
from app.core.logging import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Service for managing notifications."""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_repo = NotificationRepository(db)
        self.email_service = EmailService()
    
    async def send_entity_created_notification(
        self,
        event: NotificationEvent
    ) -> bool:
        """Send notification when an entity is created."""
        try:
            # Get active recipients for the company
            recipients = self.notification_repo.get_active_recipient_emails(event.company_id)
            
            if not recipients:
                logger.info(f"No active recipients for company {event.company_id}")
                return True  # Not an error, just no recipients
            
            # Format creation date
            created_at_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
            
            # Send email
            success = await self.email_service.send_entity_created_email(
                to=recipients,
                entity_type=event.entity_type,
                entity_name=event.entity_name,
                created_at=created_at_str,
                created_by=event.created_by,
                details=event.details
            )
            
            if success:
                logger.info(
                    f"Notification sent for {event.event_type}: "
                    f"{event.entity_name} to {len(recipients)} recipients"
                )
            else:
                logger.warning(
                    f"Failed to send notification for {event.event_type}: "
                    f"{event.entity_name}"
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return False
