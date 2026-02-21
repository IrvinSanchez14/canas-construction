"""
Tests for Visit Attachments API Endpoints

Tests the visit attachments REST API endpoints.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from httpx import AsyncClient
from io import BytesIO

from app.main import app
from app.models.project import Project, ProjectStatus
from app.models.visit import Visit, VisitStatus
from app.models.visit_attachment import VisitAttachment
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


@pytest.fixture
def mock_storage_service():
    """Mock storage service."""
    with patch('app.api.v1.visit_attachments.get_storage_service') as mock:
        service = Mock()
        service.upload_file = AsyncMock(return_value="https://cdn.example.com/visit-attachments/2026/02/test.jpg")
        service.delete_file = AsyncMock(return_value=True)
        mock.return_value = service
        yield service


@pytest.fixture
def auth_headers(sample_user):
    """Create authentication headers."""
    return {"Authorization": f"Bearer fake_token_for_{sample_user.id}"}


@pytest.mark.asyncio
async def test_upload_attachment_success(
    sample_visit,
    sample_user,
    sample_company,
    auth_headers,
    mock_storage_service
):
    """Test successful attachment upload."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        file_content = b"fake image content"
        files = {
            "file": ("test.jpg", BytesIO(file_content), "image/jpeg")
        }

        with patch('app.api.v1.visit_attachments.get_current_user', return_value=sample_user):
            response = await client.post(
                f"/api/v1/visits/{sample_visit.id}/attachments",
                params={"company_id": str(sample_company.id)},
                files=files,
                headers=auth_headers
            )

        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.jpg"
        assert data["file_type"] == "image/jpeg"
        assert "file_url" in data
        assert data["visit_id"] == str(sample_visit.id)


@pytest.mark.asyncio
async def test_upload_attachment_with_description(
    sample_visit,
    sample_user,
    sample_company,
    auth_headers,
    mock_storage_service
):
    """Test upload with description."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        file_content = b"fake pdf content"
        files = {
            "file": ("document.pdf", BytesIO(file_content), "application/pdf")
        }

        with patch('app.api.v1.visit_attachments.get_current_user', return_value=sample_user):
            response = await client.post(
                f"/api/v1/visits/{sample_visit.id}/attachments",
                params={
                    "company_id": str(sample_company.id),
                    "description": "Site inspection photo"
                },
                files=files,
                headers=auth_headers
            )

        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Site inspection photo"
        assert data["file_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_upload_attachment_max_limit_reached(
    db_session,
    sample_visit,
    sample_user,
    sample_company,
    auth_headers,
    mock_storage_service
):
    """Test that upload fails when max attachments reached."""
    # Create 20 attachments (max limit)
    for i in range(20):
        attachment = VisitAttachment(
            filename=f"file_{i}.jpg",
            file_url=f"https://cdn.example.com/file_{i}.jpg",
            file_type="image/jpeg",
            file_size=1000,
            visit_id=sample_visit.id,
            uploaded_by_user_id=sample_user.id
        )
        db_session.add(attachment)
    db_session.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        file_content = b"one too many"
        files = {
            "file": ("extra.jpg", BytesIO(file_content), "image/jpeg")
        }

        with patch('app.api.v1.visit_attachments.get_current_user', return_value=sample_user):
            response = await client.post(
                f"/api/v1/visits/{sample_visit.id}/attachments",
                params={"company_id": str(sample_company.id)},
                files=files,
                headers=auth_headers
            )

        assert response.status_code == 400
        assert "Maximum attachments" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_attachments(
    db_session,
    sample_visit,
    sample_user,
    sample_company,
    auth_headers
):
    """Test listing visit attachments."""
    # Create some attachments
    for i in range(3):
        attachment = VisitAttachment(
            filename=f"file_{i}.jpg",
            file_url=f"https://cdn.example.com/file_{i}.jpg",
            file_type="image/jpeg",
            file_size=1000 * (i + 1),
            description=f"Description {i}",
            visit_id=sample_visit.id,
            uploaded_by_user_id=sample_user.id
        )
        db_session.add(attachment)
    db_session.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.api.v1.visit_attachments.get_current_user', return_value=sample_user):
            response = await client.get(
                f"/api/v1/visits/{sample_visit.id}/attachments",
                params={"company_id": str(sample_company.id)},
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["max_allowed"] == 20
        assert len(data["attachments"]) == 3

        # Check ordering (newest first)
        filenames = [att["filename"] for att in data["attachments"]]
        assert filenames == ["file_2.jpg", "file_1.jpg", "file_0.jpg"]


@pytest.mark.asyncio
async def test_list_attachments_empty(
    sample_visit,
    sample_user,
    sample_company,
    auth_headers
):
    """Test listing when no attachments exist."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.api.v1.visit_attachments.get_current_user', return_value=sample_user):
            response = await client.get(
                f"/api/v1/visits/{sample_visit.id}/attachments",
                params={"company_id": str(sample_company.id)},
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["attachments"] == []


@pytest.mark.asyncio
async def test_delete_attachment_success(
    db_session,
    sample_visit,
    sample_user,
    sample_company,
    auth_headers,
    mock_storage_service
):
    """Test successful attachment deletion."""
    attachment = VisitAttachment(
        filename="to_delete.jpg",
        file_url="https://cdn.example.com/to_delete.jpg",
        file_type="image/jpeg",
        file_size=1000,
        visit_id=sample_visit.id,
        uploaded_by_user_id=sample_user.id
    )
    db_session.add(attachment)
    db_session.commit()
    db_session.refresh(attachment)

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.api.v1.visit_attachments.get_current_user', return_value=sample_user):
            response = await client.delete(
                f"/api/v1/visits/{sample_visit.id}/attachments/{attachment.id}",
                params={"company_id": str(sample_company.id)},
                headers=auth_headers
            )

        assert response.status_code == 204

        # Verify deletion from database
        deleted = db_session.query(VisitAttachment).filter(
            VisitAttachment.id == attachment.id
        ).first()
        assert deleted is None


@pytest.mark.asyncio
async def test_delete_attachment_not_found(
    sample_visit,
    sample_user,
    sample_company,
    auth_headers,
    mock_storage_service
):
    """Test deleting non-existent attachment."""
    from uuid import uuid4

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.api.v1.visit_attachments.get_current_user', return_value=sample_user):
            response = await client.delete(
                f"/api/v1/visits/{sample_visit.id}/attachments/{uuid4()}",
                params={"company_id": str(sample_company.id)},
                headers=auth_headers
            )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_attachment_description(
    db_session,
    sample_visit,
    sample_user,
    sample_company,
    auth_headers
):
    """Test updating attachment description."""
    attachment = VisitAttachment(
        filename="document.pdf",
        file_url="https://cdn.example.com/document.pdf",
        file_type="application/pdf",
        file_size=2000,
        description="Old description",
        visit_id=sample_visit.id,
        uploaded_by_user_id=sample_user.id
    )
    db_session.add(attachment)
    db_session.commit()
    db_session.refresh(attachment)

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.api.v1.visit_attachments.get_current_user', return_value=sample_user):
            response = await client.put(
                f"/api/v1/visits/{sample_visit.id}/attachments/{attachment.id}",
                params={"company_id": str(sample_company.id)},
                json={"description": "Updated description"},
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["filename"] == "document.pdf"


@pytest.mark.asyncio
async def test_visit_not_found(
    sample_user,
    sample_company,
    auth_headers
):
    """Test accessing attachments of non-existent visit."""
    from uuid import uuid4

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.api.v1.visit_attachments.get_current_user', return_value=sample_user):
            response = await client.get(
                f"/api/v1/visits/{uuid4()}/attachments",
                params={"company_id": str(sample_company.id)},
                headers=auth_headers
            )

        assert response.status_code == 404
