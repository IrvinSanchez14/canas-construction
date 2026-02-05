"""Tests for notification repository."""

import pytest
from uuid import uuid4

from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import (
    NotificationSettingsCreate,
    NotificationSettingsUpdate,
    NotificationRecipientCreate
)


def test_get_by_company(db_session, sample_company, sample_notification_settings):
    """Test getting notification settings by company ID."""
    repo = NotificationRepository(db_session)
    settings = repo.get_by_company(sample_company.id)
    
    assert settings is not None
    assert settings.company_id == sample_company.id
    assert settings.enabled is True


def test_get_by_company_not_found(db_session):
    """Test getting notification settings for non-existent company."""
    repo = NotificationRepository(db_session)
    settings = repo.get_by_company(uuid4())
    
    assert settings is None


def test_create_settings(db_session, sample_company):
    """Test creating notification settings."""
    repo = NotificationRepository(db_session)
    settings_create = NotificationSettingsCreate(
        company_id=sample_company.id,
        enabled=True
    )
    
    settings = repo.create_settings(sample_company.id, settings_create)
    
    assert settings.company_id == sample_company.id
    assert settings.enabled is True
    assert settings.id is not None


def test_update_settings(db_session, sample_notification_settings):
    """Test updating notification settings."""
    repo = NotificationRepository(db_session)
    settings_update = NotificationSettingsUpdate(enabled=False)
    
    updated = repo.update_settings(sample_notification_settings.id, settings_update)
    
    assert updated is not None
    assert updated.enabled is False


def test_add_recipient(db_session, sample_notification_settings):
    """Test adding a notification recipient."""
    repo = NotificationRepository(db_session)
    recipient_create = NotificationRecipientCreate(
        email="new@example.com",
        name="New User"
    )
    
    recipient = repo.add_recipient(sample_notification_settings.id, recipient_create)
    
    assert recipient.email == "new@example.com"
    assert recipient.name == "New User"
    assert recipient.is_active is True
    assert recipient.notification_setting_id == sample_notification_settings.id


def test_list_recipients_active_only(db_session, sample_notification_settings, sample_recipient):
    """Test listing active recipients only."""
    repo = NotificationRepository(db_session)
    
    # Add inactive recipient
    inactive_recipient = NotificationRecipientCreate(
        email="inactive@example.com",
        name="Inactive User"
    )
    inactive = repo.add_recipient(sample_notification_settings.id, inactive_recipient)
    inactive.is_active = False
    db_session.commit()
    
    # Get active only
    recipients = repo.list_recipients(sample_notification_settings.id, active_only=True)
    
    assert len(recipients) == 1
    assert recipients[0].email == "test@example.com"


def test_list_recipients_all(db_session, sample_notification_settings, sample_recipient):
    """Test listing all recipients."""
    repo = NotificationRepository(db_session)
    
    # Add another recipient
    repo.add_recipient(
        sample_notification_settings.id,
        NotificationRecipientCreate(email="second@example.com", name="Second User")
    )
    
    recipients = repo.list_recipients(sample_notification_settings.id, active_only=False)
    
    assert len(recipients) == 2


def test_remove_recipient(db_session, sample_recipient):
    """Test removing a recipient."""
    repo = NotificationRepository(db_session)
    
    success = repo.remove_recipient(sample_recipient.id)
    
    assert success is True
    
    # Verify it's deleted
    recipient = repo.get_recipient(sample_recipient.id)
    assert recipient is None


def test_remove_recipient_not_found(db_session):
    """Test removing non-existent recipient."""
    repo = NotificationRepository(db_session)
    
    success = repo.remove_recipient(uuid4())
    
    assert success is False


def test_get_active_recipient_emails(db_session, sample_company, sample_notification_settings, sample_recipient):
    """Test getting active recipient emails for a company."""
    repo = NotificationRepository(db_session)
    
    # Add another active recipient
    repo.add_recipient(
        sample_notification_settings.id,
        NotificationRecipientCreate(email="second@example.com", name="Second User")
    )
    
    # Add inactive recipient
    inactive = repo.add_recipient(
        sample_notification_settings.id,
        NotificationRecipientCreate(email="inactive@example.com", name="Inactive User")
    )
    inactive.is_active = False
    db_session.commit()
    
    emails = repo.get_active_recipient_emails(sample_company.id)
    
    assert len(emails) == 2
    assert "test@example.com" in emails
    assert "second@example.com" in emails
    assert "inactive@example.com" not in emails


def test_get_active_recipient_emails_disabled_settings(db_session, sample_company, sample_notification_settings):
    """Test getting emails when notifications are disabled."""
    repo = NotificationRepository(db_session)
    
    # Disable notifications
    sample_notification_settings.enabled = False
    db_session.commit()
    
    emails = repo.get_active_recipient_emails(sample_company.id)
    
    assert len(emails) == 0


def test_get_active_recipient_emails_no_settings(db_session, sample_company):
    """Test getting emails when no settings exist."""
    repo = NotificationRepository(db_session)
    
    emails = repo.get_active_recipient_emails(sample_company.id)
    
    assert len(emails) == 0
