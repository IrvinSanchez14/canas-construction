"""
Tests for Visit Attachment Schemas

Tests Pydantic validation for visit attachment schemas.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from pydantic import ValidationError

from app.schemas.visit_attachment import (
    VisitAttachmentCreate,
    VisitAttachmentUpdate,
    VisitAttachmentResponse,
    VisitAttachmentListResponse,
)


class TestVisitAttachmentCreate:
    """Tests for VisitAttachmentCreate schema."""

    def test_valid_creation(self):
        """Test creating a valid attachment schema."""
        data = VisitAttachmentCreate(
            filename="test.jpg",
            file_url="https://cdn.example.com/test.jpg",
            file_type="image/jpeg",
            file_size=1024,
            visit_id=uuid4(),
            uploaded_by_user_id=uuid4(),
            description="Test description"
        )

        assert data.filename == "test.jpg"
        assert data.file_size == 1024
        assert data.description == "Test description"

    def test_creation_without_description(self):
        """Test creating without optional description."""
        data = VisitAttachmentCreate(
            filename="test.jpg",
            file_url="https://cdn.example.com/test.jpg",
            file_type="image/jpeg",
            file_size=1024,
            visit_id=uuid4(),
        )

        assert data.description is None
        assert data.uploaded_by_user_id is None

    def test_creation_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            VisitAttachmentCreate(
                filename="test.jpg",
                # missing file_url, file_type, file_size, visit_id
            )

    def test_file_size_must_be_positive(self):
        """Test that file_size must be greater than 0."""
        with pytest.raises(ValidationError):
            VisitAttachmentCreate(
                filename="test.jpg",
                file_url="https://cdn.example.com/test.jpg",
                file_type="image/jpeg",
                file_size=0,
                visit_id=uuid4(),
            )

    def test_description_max_length(self):
        """Test description max length validation."""
        with pytest.raises(ValidationError):
            VisitAttachmentCreate(
                filename="test.jpg",
                file_url="https://cdn.example.com/test.jpg",
                file_type="image/jpeg",
                file_size=1024,
                visit_id=uuid4(),
                description="x" * 1001
            )


class TestVisitAttachmentUpdate:
    """Tests for VisitAttachmentUpdate schema."""

    def test_valid_update(self):
        """Test valid description update."""
        data = VisitAttachmentUpdate(description="New description")
        assert data.description == "New description"

    def test_update_null_description(self):
        """Test setting description to null."""
        data = VisitAttachmentUpdate(description=None)
        assert data.description is None

    def test_update_empty_description(self):
        """Test empty description."""
        data = VisitAttachmentUpdate()
        assert data.description is None


class TestVisitAttachmentResponse:
    """Tests for VisitAttachmentResponse schema."""

    def test_valid_response(self):
        """Test valid response schema."""
        visit_id = uuid4()
        user_id = uuid4()
        attachment_id = uuid4()
        now = datetime.utcnow()

        data = VisitAttachmentResponse(
            id=attachment_id,
            filename="test.jpg",
            file_url="https://cdn.example.com/test.jpg",
            file_type="image/jpeg",
            file_size=1024,
            description="Test",
            visit_id=visit_id,
            uploaded_by_user_id=user_id,
            uploaded_by_name="Test User",
            created_at=now,
            updated_at=now,
        )

        assert data.id == attachment_id
        assert data.visit_id == visit_id
        assert data.uploaded_by_name == "Test User"

    def test_response_without_user_info(self):
        """Test response when uploader info is absent."""
        data = VisitAttachmentResponse(
            id=uuid4(),
            filename="test.jpg",
            file_url="https://cdn.example.com/test.jpg",
            file_type="image/jpeg",
            file_size=1024,
            description=None,
            visit_id=uuid4(),
            uploaded_by_user_id=None,
            uploaded_by_name=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert data.uploaded_by_user_id is None
        assert data.uploaded_by_name is None


class TestVisitAttachmentListResponse:
    """Tests for VisitAttachmentListResponse schema."""

    def test_empty_list(self):
        """Test empty list response."""
        data = VisitAttachmentListResponse(
            attachments=[],
            total=0,
            max_allowed=20,
        )

        assert data.total == 0
        assert data.max_allowed == 20
        assert len(data.attachments) == 0

    def test_default_max_allowed(self):
        """Test default max_allowed value."""
        data = VisitAttachmentListResponse(
            attachments=[],
            total=0,
        )

        assert data.max_allowed == 20
