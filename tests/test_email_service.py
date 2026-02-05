"""Tests for email service."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.services.email_service import EmailService


@pytest.fixture
def email_service():
    """Create email service instance."""
    with patch('app.services.email_service.resend'):
        service = EmailService()
        return service


@pytest.mark.asyncio
async def test_send_email_success(email_service):
    """Test successful email sending."""
    with patch('app.services.email_service.resend.Emails.send') as mock_send:
        mock_send.return_value = {'id': 'test-email-id'}
        
        success = await email_service.send_email(
            to=["test@example.com"],
            subject="Test Subject",
            html="<p>Test content</p>"
        )
        
        assert success is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["to"] == ["test@example.com"]
        assert call_args["subject"] == "Test Subject"
        assert call_args["html"] == "<p>Test content</p>"


@pytest.mark.asyncio
async def test_send_email_with_custom_from(email_service):
    """Test sending email with custom from address."""
    with patch('app.services.email_service.resend.Emails.send') as mock_send:
        mock_send.return_value = {'id': 'test-email-id'}
        
        success = await email_service.send_email(
            to=["test@example.com"],
            subject="Test Subject",
            html="<p>Test content</p>",
            from_email="custom@example.com",
            from_name="Custom Name"
        )
        
        assert success is True
        call_args = mock_send.call_args[0][0]
        assert call_args["from"] == "Custom Name <custom@example.com>"


@pytest.mark.asyncio
async def test_send_email_failure(email_service):
    """Test email sending failure."""
    with patch('app.services.email_service.resend.Emails.send') as mock_send:
        mock_send.side_effect = Exception("Resend API error")
        
        success = await email_service.send_email(
            to=["test@example.com"],
            subject="Test Subject",
            html="<p>Test content</p>"
        )
        
        assert success is False


@pytest.mark.asyncio
async def test_send_entity_created_email_success(email_service):
    """Test sending entity created notification."""
    with patch('app.services.email_service.resend.Emails.send') as mock_send:
        mock_send.return_value = {'id': 'test-email-id'}
        
        success = await email_service.send_entity_created_email(
            to=["test@example.com"],
            entity_type="Project",
            entity_name="New Project",
            created_at=datetime.now().isoformat(),
            created_by="John Doe",
            details={"budget": "$100,000"},
            company_name="Test Company"
        )
        
        assert success is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["subject"] == "New Project Created: New Project"


@pytest.mark.asyncio
async def test_send_entity_created_email_failure(email_service):
    """Test entity created email failure."""
    with patch('app.services.email_service.resend.Emails.send') as mock_send:
        mock_send.side_effect = Exception("Email error")
        
        success = await email_service.send_entity_created_email(
            to=["test@example.com"],
            entity_type="Project",
            entity_name="New Project",
            created_at=datetime.now().isoformat()
        )
        
        assert success is False


def test_render_template_success(email_service):
    """Test template rendering."""
    html = email_service.render_template(
        "entity_created.html",
        entity_type="Project",
        entity_name="Test Project",
        created_at="2026-01-01",
        created_by="John Doe",
        details={},
        company_name="Test Company"
    )
    
    assert html is not None
    assert "Test Project" in html
    assert "Project" in html


def test_render_template_failure(email_service):
    """Test template rendering with non-existent template."""
    with pytest.raises(Exception):
        email_service.render_template("non_existent.html")


@pytest.mark.asyncio
async def test_send_multiple_recipients(email_service):
    """Test sending email to multiple recipients."""
    with patch('app.services.email_service.resend.Emails.send') as mock_send:
        mock_send.return_value = {'id': 'test-email-id'}
        
        recipients = ["test1@example.com", "test2@example.com", "test3@example.com"]
        success = await email_service.send_email(
            to=recipients,
            subject="Test Subject",
            html="<p>Test content</p>"
        )
        
        assert success is True
        call_args = mock_send.call_args[0][0]
        assert call_args["to"] == recipients
