from fastapi import APIRouter, status
from datetime import datetime
from app.core.config import settings

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """
    Health check endpoint for AWS ELB/ALB target group health checks.
    Returns 200 OK if the service is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION,
    }


@router.get("/health/ready", status_code=status.HTTP_200_OK, tags=["Health"])
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes/ECS readiness probes.
    Check if the application is ready to serve traffic.
    """
    # Add checks for database, redis, etc.
    # For now, return ready if we can respond
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/live", status_code=status.HTTP_200_OK, tags=["Health"])
async def liveness_check():
    """
    Liveness check endpoint for Kubernetes/ECS liveness probes.
    Check if the application is alive and not deadlocked.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }
