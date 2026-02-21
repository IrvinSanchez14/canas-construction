"""
Tests for Visit Attachment Model

Tests the VisitAttachment model and its relationships.
"""

import pytest
from datetime import datetime

from app.models.visit_attachment import VisitAttachment
from app.models.visit import Visit, VisitStatus
from app.models.project import Project, ProjectStatus
from app.models.client import Client
from app.models.project_category import ProjectCategory
from app.models.user import User
from app.models.company import Company


@pytest.fixture
def sample_company(db_session):
    """Create a sample company."""
    company = Company(
        name="Test Company",
        email="test@company.com",
        phone="555-0000",
        address="123 Test St"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def sample_user(db_session, sample_company):
    """Create a sample user."""
    user = User(
        first_name="Test",
        last_name="User",
        username="testuser",
        email="testuser@example.com",
        hashed_password="hashedpassword",
        company_id=sample_company.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_client(db_session, sample_company):
    """Create a sample client."""
    client = Client(
        name="Test Client",
        email="client@example.com",
        phone="555-1234",
        company_id=sample_company.id
    )
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


@pytest.fixture
def sample_category(db_session, sample_company):
    """Create a sample project category."""
    category = ProjectCategory(
        name="Test Category",
        description="Test category description",
        company_id=sample_company.id
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def sample_project(db_session, sample_client, sample_category, sample_user):
    """Create a sample project."""
    project = Project(
        name="Test Project",
        description="Test project description",
        status=ProjectStatus.IN_PROGRESS,
        client_id=sample_client.id,
        category_id=sample_category.id,
        created_by_user_id=sample_user.id
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def sample_visit(db_session, sample_project, sample_user):
    """Create a sample visit."""
    visit = Visit(
        title="Test Visit",
        description="Test visit description",
        status=VisitStatus.PLANNING,
        project_id=sample_project.id,
        created_by_user_id=sample_user.id
    )
    db_session.add(visit)
    db_session.commit()
    db_session.refresh(visit)
    return visit


def test_create_visit_attachment(db_session, sample_visit, sample_user):
    """Test creating a visit attachment."""
    attachment = VisitAttachment(
        filename="test_image.jpg",
        file_url="https://cdn.example.com/visit-attachments/2026/02/abc123.jpg",
        file_type="image/jpeg",
        file_size=1024000,
        description="Test image description",
        visit_id=sample_visit.id,
        uploaded_by_user_id=sample_user.id
    )

    db_session.add(attachment)
    db_session.commit()
    db_session.refresh(attachment)

    assert attachment.id is not None
    assert attachment.filename == "test_image.jpg"
    assert attachment.file_url == "https://cdn.example.com/visit-attachments/2026/02/abc123.jpg"
    assert attachment.file_type == "image/jpeg"
    assert attachment.file_size == 1024000
    assert attachment.description == "Test image description"
    assert attachment.visit_id == sample_visit.id
    assert attachment.uploaded_by_user_id == sample_user.id
    assert isinstance(attachment.created_at, datetime)
    assert isinstance(attachment.updated_at, datetime)


def test_attachment_without_description(db_session, sample_visit, sample_user):
    """Test creating attachment without description."""
    attachment = VisitAttachment(
        filename="document.pdf",
        file_url="https://cdn.example.com/visit-attachments/2026/02/def456.pdf",
        file_type="application/pdf",
        file_size=2048000,
        description=None,
        visit_id=sample_visit.id,
        uploaded_by_user_id=sample_user.id
    )

    db_session.add(attachment)
    db_session.commit()
    db_session.refresh(attachment)

    assert attachment.description is None
    assert attachment.file_type == "application/pdf"


def test_attachment_visit_relationship(db_session, sample_visit, sample_user):
    """Test attachment-visit relationship."""
    attachment = VisitAttachment(
        filename="test.jpg",
        file_url="https://cdn.example.com/test.jpg",
        file_type="image/jpeg",
        file_size=1000,
        visit_id=sample_visit.id,
        uploaded_by_user_id=sample_user.id
    )

    db_session.add(attachment)
    db_session.commit()
    db_session.refresh(attachment)

    # Test forward relationship
    assert attachment.visit is not None
    assert attachment.visit.id == sample_visit.id
    assert attachment.visit.title == "Test Visit"

    # Test backward relationship
    db_session.refresh(sample_visit)
    assert len(sample_visit.visit_attachments) == 1
    assert sample_visit.visit_attachments[0].id == attachment.id


def test_attachment_user_relationship(db_session, sample_visit, sample_user):
    """Test attachment-user relationship."""
    attachment = VisitAttachment(
        filename="test.jpg",
        file_url="https://cdn.example.com/test.jpg",
        file_type="image/jpeg",
        file_size=1000,
        visit_id=sample_visit.id,
        uploaded_by_user_id=sample_user.id
    )

    db_session.add(attachment)
    db_session.commit()
    db_session.refresh(attachment)

    assert attachment.uploaded_by is not None
    assert attachment.uploaded_by.id == sample_user.id
    assert attachment.uploaded_by.full_name == "Test User"


def test_attachment_cascade_delete(db_session, sample_visit, sample_user):
    """Test that attachments are deleted when visit is deleted."""
    attachment = VisitAttachment(
        filename="test.jpg",
        file_url="https://cdn.example.com/test.jpg",
        file_type="image/jpeg",
        file_size=1000,
        visit_id=sample_visit.id,
        uploaded_by_user_id=sample_user.id
    )

    db_session.add(attachment)
    db_session.commit()

    attachment_id = attachment.id

    # Delete visit
    db_session.delete(sample_visit)
    db_session.commit()

    # Verify attachment was deleted
    deleted_attachment = db_session.query(VisitAttachment).filter(
        VisitAttachment.id == attachment_id
    ).first()

    assert deleted_attachment is None


@pytest.mark.skip(reason="ON DELETE SET NULL not enforced by SQLite; works in PostgreSQL")
def test_attachment_user_set_null_on_delete(db_session, sample_visit, sample_user):
    """Test that uploaded_by_user_id is set to NULL when user is deleted."""
    attachment = VisitAttachment(
        filename="test.jpg",
        file_url="https://cdn.example.com/test.jpg",
        file_type="image/jpeg",
        file_size=1000,
        visit_id=sample_visit.id,
        uploaded_by_user_id=sample_user.id
    )

    db_session.add(attachment)
    db_session.commit()

    attachment_id = attachment.id

    # Delete user
    db_session.delete(sample_user)
    db_session.commit()

    # Verify attachment still exists but user is NULL
    attachment = db_session.query(VisitAttachment).filter(
        VisitAttachment.id == attachment_id
    ).first()

    assert attachment is not None
    assert attachment.uploaded_by_user_id is None


def test_multiple_attachments_per_visit(db_session, sample_visit, sample_user):
    """Test adding multiple attachments to a visit."""
    for i in range(5):
        attachment = VisitAttachment(
            filename=f"file_{i}.jpg",
            file_url=f"https://cdn.example.com/file_{i}.jpg",
            file_type="image/jpeg",
            file_size=1000 * (i + 1),
            description=f"File {i}",
            visit_id=sample_visit.id,
            uploaded_by_user_id=sample_user.id
        )
        db_session.add(attachment)

    db_session.commit()

    # Verify all attachments were created
    db_session.refresh(sample_visit)
    assert len(sample_visit.visit_attachments) == 5

    # Verify they're in the database
    count = db_session.query(VisitAttachment).filter(
        VisitAttachment.visit_id == sample_visit.id
    ).count()
    assert count == 5


def test_attachment_repr(db_session, sample_visit, sample_user):
    """Test attachment string representation."""
    attachment = VisitAttachment(
        filename="test.jpg",
        file_url="https://cdn.example.com/test.jpg",
        file_type="image/jpeg",
        file_size=1000,
        visit_id=sample_visit.id,
        uploaded_by_user_id=sample_user.id
    )

    db_session.add(attachment)
    db_session.commit()
    db_session.refresh(attachment)

    repr_str = repr(attachment)
    assert "VisitAttachment" in repr_str
    assert str(attachment.id) in repr_str
    assert "test.jpg" in repr_str
    assert str(sample_visit.id) in repr_str
