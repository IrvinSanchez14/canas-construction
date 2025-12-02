from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from mangum import Mangum

from app.core.config import settings
from app.core.logging import AppLogger, get_logger
from app.core.error_handlers import register_exception_handlers
from app.api.routes import api_router

# Setup logging
AppLogger.setup_logging()
logger = get_logger(__name__)


class OPTIONSHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle OPTIONS requests before they reach endpoints.
    
    This is the KEY solution - it intercepts OPTIONS requests BEFORE FastAPI
    tries to validate them, preventing 400 errors and ensuring CORS headers
    are always present.
    
    For now: allows ANY origin (development mode)
    TODO: Add origin validation for production
    """
    
    async def dispatch(self, request: Request, call_next):
        # Handle OPTIONS requests immediately - BEFORE they reach endpoints
        if request.method == "OPTIONS":
            origin = request.headers.get("origin", "*")
            
            # Allow ANY origin - we'll restrict in production later
            response = Response(status_code=200)
            response.headers["Access-Control-Allow-Origin"] = origin if origin != "*" else "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "3600"
            
            logger.debug(f"OPTIONS request handled for origin: {origin}")
            return response
        
        # For non-OPTIONS requests, continue normally
        response = await call_next(request)
        return response


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

    # OPTIONS Handler Middleware - Handle OPTIONS requests BEFORE they reach endpoints
    # THIS IS THE KEY FIX - intercepts OPTIONS before FastAPI validation
    # This must be added FIRST to intercept OPTIONS before validation errors occur
    app.add_middleware(OPTIONSHandlerMiddleware)
    
    # CORS Middleware - Allow ALL origins (development mode)
    # TODO: Restrict to specific origins in production
    logger.info("CORS: Allowing ALL origins (development mode)")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=False,  # Must be False when using allow_origins=["*"]
        allow_methods=["*"],  # Allow all methods including OPTIONS
        allow_headers=["*"],  # Allow all headers
        expose_headers=["*"],  # Expose all headers
        max_age=3600,  # Cache preflight requests for 1 hour
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
        logger.info(f"CORS Origins: {settings.CORS_ORIGINS}")
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
