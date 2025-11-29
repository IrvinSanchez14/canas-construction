from fastapi import APIRouter
from app.api import health
from app.api.v1 import auth, companies, roles, users, clients, project_categories, projects, catalog_items

api_router = APIRouter()

# Health check
api_router.include_router(health.router, tags=["Health"])

# Authentication (NO AUTH REQUIRED - generates tokens)
api_router.include_router(auth.router)

# Main API endpoints (enterprise-grade architecture)
# TODO: Add authentication to these endpoints using Depends(get_current_active_user)
api_router.include_router(companies.router)
api_router.include_router(roles.router)
api_router.include_router(users.router)

# CRM endpoints
# TODO: Add authentication to these endpoints using Depends(get_current_active_user)
api_router.include_router(clients.router)
api_router.include_router(project_categories.router)
api_router.include_router(projects.router)
api_router.include_router(catalog_items.router)
