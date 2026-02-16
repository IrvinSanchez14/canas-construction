"""
Storage Service for Cloudflare R2 (S3-compatible)

Handles file uploads and management for rendering images.
"""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Optional
from uuid import uuid4
from datetime import datetime
import mimetypes

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageService:
    """
    Service for handling file uploads to Cloudflare R2.

    R2 is S3-compatible, so we use boto3 with a custom endpoint.
    """

    ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
    ALLOWED_DOCUMENT_TYPES = {'application/pdf'}
    ALLOWED_FILE_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_DOCUMENT_TYPES  # Combined set
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    def __init__(self):
        """Initialize R2 client."""
        if not all([
            settings.R2_ACCOUNT_ID,
            settings.R2_ACCESS_KEY_ID,
            settings.R2_SECRET_ACCESS_KEY,
            settings.R2_BUCKET_NAME
        ]):
            logger.warning("R2 configuration incomplete. File uploads will fail.")
            self.client = None
            return

        # R2 endpoint URL
        endpoint_url = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

        self.client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(
                signature_version='s3v4',
                retries={'max_attempts': 3}
            )
        )
        self.bucket_name = settings.R2_BUCKET_NAME
        self.public_url = settings.R2_PUBLIC_URL

    def _generate_key(self, filename: str, folder: str = "renderings") -> str:
        """
        Generate a unique key for the file.

        Format: folder/YYYY/MM/uuid_filename
        """
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
        unique_id = uuid4().hex[:12]
        date_prefix = datetime.utcnow().strftime("%Y/%m")
        return f"{folder}/{date_prefix}/{unique_id}.{ext}"

    def _get_content_type(self, filename: str) -> str:
        """Get content type from filename."""
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or 'application/octet-stream'

    def validate_image(self, content_type: str, file_size: int) -> tuple[bool, str]:
        """
        Validate image file.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if content_type not in self.ALLOWED_IMAGE_TYPES:
            return False, f"Invalid file type: {content_type}. Allowed: JPEG, PNG, WebP, GIF"

        if file_size > self.MAX_FILE_SIZE:
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            return False, f"File too large. Maximum size: {max_mb}MB"

        return True, ""

    def validate_file(self, content_type: str, file_size: int) -> tuple[bool, str]:
        """
        Validate any file (image or document).

        Returns:
            Tuple of (is_valid, error_message)
        """
        if content_type not in self.ALLOWED_FILE_TYPES:
            return False, f"Invalid file type: {content_type}. Allowed: JPEG, PNG, WebP, GIF, PDF"

        if file_size > self.MAX_FILE_SIZE:
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            return False, f"File too large. Maximum size: {max_mb}MB"

        return True, ""

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        folder: str = "renderings",
        validate_images_only: bool = False
    ) -> Optional[str]:
        """
        Upload a file to R2.

        Args:
            file_content: File bytes
            filename: Original filename
            content_type: MIME type
            folder: Folder prefix in bucket
            validate_images_only: If True, only validate images; if False, validate all file types

        Returns:
            Public URL of uploaded file, or None if failed
        """
        if not self.client:
            raise ValueError("R2 storage not configured")

        # Validate
        if validate_images_only:
            is_valid, error = self.validate_image(content_type, len(file_content))
        else:
            is_valid, error = self.validate_file(content_type, len(file_content))
            
        if not is_valid:
            raise ValueError(error)

        # Generate unique key
        key = self._generate_key(filename, folder)

        try:
            # Upload to R2
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type,
            )

            # Generate URL
            if self.public_url:
                url = f"{self.public_url.rstrip('/')}/{key}"
            else:
                # Use R2.dev public URL (requires public bucket)
                url = f"https://{self.bucket_name}.{settings.R2_ACCOUNT_ID}.r2.dev/{key}"

            logger.info(f"Uploaded file to R2: {key}")
            return url

        except ClientError as e:
            logger.error(f"Failed to upload to R2: {e}")
            raise ValueError(f"Upload failed: {str(e)}")

    async def delete_file(self, url: str) -> bool:
        """
        Delete a file from R2 by its URL.

        Args:
            url: Full URL of the file

        Returns:
            True if deleted, False otherwise
        """
        if not self.client:
            return False

        try:
            # Extract key from URL
            # URL format: https://bucket.account.r2.dev/folder/date/filename
            # or custom domain: https://cdn.example.com/folder/date/filename
            if self.public_url and url.startswith(self.public_url):
                key = url.replace(self.public_url.rstrip('/') + '/', '')
            else:
                # Extract path after domain
                parts = url.split('/')
                # Find index after the domain
                key = '/'.join(parts[3:])

            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            logger.info(f"Deleted file from R2: {key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete from R2: {e}")
            return False

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for direct upload.

        Args:
            key: Object key in bucket
            expiration: URL expiration in seconds

        Returns:
            Presigned URL or None if failed
        """
        if not self.client:
            return None

        try:
            url = self.client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None


# Singleton instance
storage_service = StorageService()


def get_storage_service() -> StorageService:
    """Dependency injection for storage service."""
    return storage_service
