from fastapi import APIRouter
from app.api import health

api_router = APIRouter()

# Include all route modules here
api_router.include_router(health.router, tags=["Health"])

# Add your other routers here as you build them
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
# api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
