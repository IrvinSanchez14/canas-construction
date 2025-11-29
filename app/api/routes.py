from fastapi import APIRouter
from app.api import health
from app.api.v1 import companies, roles, users, clients, project_categories, projects

api_router = APIRouter()

# Health check
api_router.include_router(health.router, tags=["Health"])

# Main API endpoints (enterprise-grade architecture)
api_router.include_router(companies.router)
api_router.include_router(roles.router)
api_router.include_router(users.router)

# CRM endpoints
api_router.include_router(clients.router)
api_router.include_router(project_categories.router)
api_router.include_router(projects.router)
