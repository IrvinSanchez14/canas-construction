from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from mangum import Mangum

from app.core.config import settings
from app.core.logging import AppLogger, get_logger
from app.core.error_handlers import register_exception_handlers
from app.api.routes import api_router

# Setup logging
AppLogger.setup_logging()
logger = get_logger(__name__)


def create_application() -> FastAPI:
    """Application factory for creating FastAPI instance."""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Construction Management API",
        docs_url=f"{settings.API_PREFIX}/docs" if settings.DEBUG else None,
        redoc_url=f"{settings.API_PREFIX}/redoc" if settings.DEBUG else None,
        openapi_url=f"{settings.API_PREFIX}/openapi.json" if settings.DEBUG else None,
    )

    # CORS Middleware - Important for frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # GZip Middleware - Compress responses for better performance
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Trusted Host Middleware - Security for production
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*.amazonaws.com", "*.compute.amazonaws.com"]
        )

    # Register exception handlers
    register_exception_handlers(app)

    # Include API router
    app.include_router(api_router, prefix=settings.API_PREFIX)

    # Startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Debug mode: {settings.DEBUG}")
        logger.info("Architecture: Enterprise-grade with DI, Repository Pattern, SOLID principles")

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info(f"Shutting down {settings.APP_NAME}")

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "message": f"Welcome to {settings.APP_NAME}",
            "version": settings.APP_VERSION,
            "docs": f"{settings.API_PREFIX}/docs" if settings.DEBUG else "disabled",
            "architecture": "Enterprise-grade: SOLID, DI, Repository Pattern, N+1 Optimized",
        }

    return app


# Create FastAPI application
app = create_application()

# AWS Lambda handler using Mangum
# This allows the same app to run on EC2, ECS, or Lambda
handler = Mangum(app, lifespan="off")
