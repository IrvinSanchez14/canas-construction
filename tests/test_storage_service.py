"""
Tests for Storage Service

Tests the enhanced storage service with PDF support.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from app.services.storage_service import StorageService


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    return Mock()


@pytest.fixture
def storage_service(mock_s3_client):
    """Create a storage service with mocked client."""
    service = StorageService()
    service.client = mock_s3_client
    service.bucket_name = "test-bucket"
    service.public_url = "https://cdn.example.com"
    return service


def test_validate_image_success(storage_service):
    """Test validating a valid image."""
    is_valid, error = storage_service.validate_image(
        content_type="image/jpeg",
        file_size=5 * 1024 * 1024  # 5MB
    )
    
    assert is_valid is True
    assert error == ""


def test_validate_image_invalid_type(storage_service):
    """Test validating invalid image type."""
    is_valid, error = storage_service.validate_image(
        content_type="application/pdf",
        file_size=1024
    )
    
    assert is_valid is False
    assert "Invalid file type" in error


def test_validate_image_too_large(storage_service):
    """Test validating oversized image."""
    is_valid, error = storage_service.validate_image(
        content_type="image/jpeg",
        file_size=15 * 1024 * 1024  # 15MB (over 10MB limit)
    )
    
    assert is_valid is False
    assert "too large" in error.lower()


def test_validate_file_success_image(storage_service):
    """Test validating a valid image file."""
    is_valid, error = storage_service.validate_file(
        content_type="image/png",
        file_size=2 * 1024 * 1024  # 2MB
    )
    
    assert is_valid is True
    assert error == ""


def test_validate_file_success_pdf(storage_service):
    """Test validating a valid PDF file."""
    is_valid, error = storage_service.validate_file(
        content_type="application/pdf",
        file_size=8 * 1024 * 1024  # 8MB
    )
    
    assert is_valid is True
    assert error == ""


def test_validate_file_invalid_type(storage_service):
    """Test validating invalid file type."""
    is_valid, error = storage_service.validate_file(
        content_type="application/msword",
        file_size=1024
    )
    
    assert is_valid is False
    assert "Invalid file type" in error


def test_validate_file_too_large(storage_service):
    """Test validating oversized file."""
    is_valid, error = storage_service.validate_file(
        content_type="application/pdf",
        file_size=20 * 1024 * 1024  # 20MB
    )
    
    assert is_valid is False
    assert "too large" in error.lower()


def test_allowed_file_types(storage_service):
    """Test that all expected file types are allowed."""
    expected_types = {
        'image/jpeg',
        'image/png',
        'image/webp',
        'image/gif',
        'application/pdf'
    }
    
    assert storage_service.ALLOWED_FILE_TYPES == expected_types


@pytest.mark.asyncio
async def test_upload_file_image_only_validation(storage_service, mock_s3_client):
    """Test upload with image-only validation."""
    mock_s3_client.put_object.return_value = {}
    
    file_content = b"fake image content"
    
    url = await storage_service.upload_file(
        file_content=file_content,
        filename="test.jpg",
        content_type="image/jpeg",
        folder="attachments",
        validate_images_only=True
    )
    
    assert url is not None
    assert "attachments/" in url
    mock_s3_client.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_upload_file_pdf_fails_with_image_validation(storage_service, mock_s3_client):
    """Test that PDF upload fails with image-only validation."""
    file_content = b"fake pdf content"
    
    with pytest.raises(ValueError) as exc_info:
        await storage_service.upload_file(
            file_content=file_content,
            filename="document.pdf",
            content_type="application/pdf",
            folder="attachments",
            validate_images_only=True
        )
    
    assert "Invalid file type" in str(exc_info.value)
    mock_s3_client.put_object.assert_not_called()


@pytest.mark.asyncio
async def test_upload_file_pdf_succeeds_with_all_validation(storage_service, mock_s3_client):
    """Test that PDF upload succeeds with all file type validation."""
    mock_s3_client.put_object.return_value = {}
    
    file_content = b"fake pdf content"
    
    url = await storage_service.upload_file(
        file_content=file_content,
        filename="document.pdf",
        content_type="application/pdf",
        folder="attachments",
        validate_images_only=False
    )
    
    assert url is not None
    assert "attachments/" in url
    mock_s3_client.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_upload_file_generates_unique_key(storage_service, mock_s3_client):
    """Test that uploaded files get unique keys."""
    mock_s3_client.put_object.return_value = {}
    
    file_content = b"test content"
    
    url1 = await storage_service.upload_file(
        file_content=file_content,
        filename="test.jpg",
        content_type="image/jpeg",
        folder="attachments",
        validate_images_only=False
    )
    
    url2 = await storage_service.upload_file(
        file_content=file_content,
        filename="test.jpg",
        content_type="image/jpeg",
        folder="attachments",
        validate_images_only=False
    )
    
    # URLs should be different (different unique IDs)
    assert url1 != url2


@pytest.mark.asyncio
async def test_upload_file_no_client(storage_service):
    """Test upload fails when client is not configured."""
    storage_service.client = None
    
    with pytest.raises(ValueError) as exc_info:
        await storage_service.upload_file(
            file_content=b"test",
            filename="test.jpg",
            content_type="image/jpeg",
            folder="attachments"
        )
    
    assert "not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_file_client_error(storage_service, mock_s3_client):
    """Test upload handles client errors."""
    mock_s3_client.put_object.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
        'PutObject'
    )
    
    with pytest.raises(ValueError) as exc_info:
        await storage_service.upload_file(
            file_content=b"test content",
            filename="test.jpg",
            content_type="image/jpeg",
            folder="attachments"
        )
    
    assert "Upload failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_file_success(storage_service, mock_s3_client):
    """Test successful file deletion."""
    mock_s3_client.delete_object.return_value = {}
    
    url = "https://cdn.example.com/attachments/2026/02/abc123.jpg"
    result = await storage_service.delete_file(url)
    
    assert result is True
    mock_s3_client.delete_object.assert_called_once()


@pytest.mark.asyncio
async def test_delete_file_no_client(storage_service):
    """Test delete returns False when client not configured."""
    storage_service.client = None
    
    result = await storage_service.delete_file("https://example.com/file.jpg")
    
    assert result is False


@pytest.mark.asyncio
async def test_delete_file_client_error(storage_service, mock_s3_client):
    """Test delete handles client errors gracefully."""
    mock_s3_client.delete_object.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchKey', 'Message': 'Not Found'}},
        'DeleteObject'
    )
    
    result = await storage_service.delete_file(
        "https://cdn.example.com/attachments/2026/02/abc123.jpg"
    )
    
    assert result is False


def test_generate_key_format(storage_service):
    """Test that generated keys follow expected format."""
    key = storage_service._generate_key("test.jpg", "attachments")
    
    # Should be: attachments/YYYY/MM/uniqueid.jpg
    parts = key.split('/')
    assert len(parts) == 4
    assert parts[0] == "attachments"
    assert len(parts[1]) == 4  # Year
    assert len(parts[2]) == 2  # Month
    assert parts[3].endswith('.jpg')


def test_get_content_type(storage_service):
    """Test content type detection."""
    assert storage_service._get_content_type("image.jpg") == "image/jpeg"
    assert storage_service._get_content_type("document.pdf") == "application/pdf"
    assert storage_service._get_content_type("photo.png") == "image/png"
    assert storage_service._get_content_type("unknown.xyz") == "application/octet-stream"
