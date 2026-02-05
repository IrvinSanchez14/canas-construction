"""
Helper utilities for sending notifications across the application.
"""

import asyncio
from typing import Optional, Dict
from uuid import UUID

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.notification import NotificationEvent

logger = get_logger(__name__)


async def send_notification_async(
    db,
    event_type: str,
    entity_type: str,
    entity_id: UUID,
    entity_name: str,
    company_id: UUID,
    created_by: Optional[str] = None,
    details: Optional[Dict] = None
):
    """
    Send notification asynchronously without blocking the request.
    
    Args:
        db: Database session
        event_type: Event type (e.g., "client.created")
        entity_type: Entity type (e.g., "Client")
        entity_id: Entity ID
        entity_name: Entity name
        company_id: Company ID
        created_by: Creator email/name
        details: Additional details dict
    """
    if not settings.NOTIFICATIONS_ENABLED:
        return
    
    try:
        from app.services.notification_service import NotificationService
        
        notification_service = NotificationService(db)
        event = NotificationEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            company_id=company_id,
            created_by=created_by,
            details=details
        )
        
        await notification_service.send_entity_created_notification(event)
        
    except Exception as e:
        logger.error(f"Failed to send notification for {event_type}: {str(e)}")
        # Don't raise - notifications shouldn't fail the main request


def send_notification_background(
    db,
    event_type: str,
    entity_type: str,
    entity_id: UUID,
    entity_name: str,
    company_id: UUID,
    created_by: Optional[str] = None,
    details: Optional[Dict] = None
):
    """
    Send notification in the background (fire and forget).
    
    This is a convenience wrapper that creates a background task.
    """
    try:
        # Create event loop and run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            send_notification_async(
                db, event_type, entity_type, entity_id,
                entity_name, company_id, created_by, details
            )
        )
        loop.close()
    except Exception as e:
        logger.error(f"Background notification failed: {str(e)}")
