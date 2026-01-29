"""
Upload API endpoints for file management.

Handles image uploads to Cloudflare R2 storage.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from pydantic import BaseModel
from uuid import UUID

from app.services.storage_service import get_storage_service, StorageService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])


class UploadResponse(BaseModel):
    """Response schema for file upload."""
    url: str
    filename: str
    content_type: str
    size: int


@router.post("/image", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(..., description="Image file (JPEG, PNG, WebP, GIF)"),
    company_id: UUID = Query(..., description="Company ID for validation"),
    folder: str = Query("renderings", description="Storage folder"),
    storage: StorageService = Depends(get_storage_service)
):
    """
    Upload an image file to cloud storage.

    Supported formats: JPEG, PNG, WebP, GIF
    Maximum size: 10MB

    Returns the public URL of the uploaded image.
    """
    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate content type
    content_type = file.content_type or 'application/octet-stream'

    try:
        # Upload to R2
        url = await storage.upload_file(
            file_content=content,
            filename=file.filename or 'image.jpg',
            content_type=content_type,
            folder=folder
        )

        logger.info(f"Image uploaded successfully: {url}")

        return UploadResponse(
            url=url,
            filename=file.filename or 'image.jpg',
            content_type=content_type,
            size=file_size
        )

    except ValueError as e:
        logger.warning(f"Upload validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image")


@router.delete("/image")
async def delete_image(
    url: str = Query(..., description="URL of the image to delete"),
    company_id: UUID = Query(..., description="Company ID for validation"),
    storage: StorageService = Depends(get_storage_service)
):
    """
    Delete an image from cloud storage.

    Note: This only deletes from storage, not from database records.
    """
    try:
        success = await storage.delete_file(url)

        if success:
            return {"message": "Image deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Image not found or already deleted")

    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete image")
