# Canas Construction API - Developer Documentation

> **Purpose:** This document provides comprehensive understanding of the Canas Construction API architecture, patterns, business logic, and coding conventions for efficient development and maintenance.

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Core Patterns & Principles](#core-patterns--principles)
5. [Database Models & Relationships](#database-models--relationships)
6. [Business Logic Flow](#business-logic-flow)
7. [Authentication & Authorization](#authentication--authorization)
8. [API Endpoints Structure](#api-endpoints-structure)
9. [Multi-Tenant Architecture](#multi-tenant-architecture)
10. [Development Guidelines](#development-guidelines)
11. [Common Operations](#common-operations)
12. [Deployment & AWS](#deployment--aws)

---

## Architecture Overview

### 🏗️ Enterprise-Grade Clean Architecture

The API follows **SOLID principles** with a **layered architecture**:

```
┌─────────────────────────────────────┐
│   API Layer (FastAPI Routes)       │  ← HTTP Endpoints
├─────────────────────────────────────┤
│   Service Layer (Business Logic)   │  ← Business Rules
├─────────────────────────────────────┤
│   Repository Layer (Data Access)   │  ← Database Operations
├─────────────────────────────────────┤
│   Model Layer (SQLAlchemy ORM)     │  ← Data Structure
└─────────────────────────────────────┘
```

**Key Architectural Principles:**
- ✅ **Dependency Injection (DI)** - All dependencies injected via constructors
- ✅ **Repository Pattern** - Data access abstracted from business logic
- ✅ **Service Layer** - Business logic isolated and testable
- ✅ **N+1 Query Optimization** - Eager loading with `joinedload()`
- ✅ **Multi-Tenant Isolation** - Company-based data segregation
- ✅ **Transaction Management** - Automatic commit/rollback

---

## Technology Stack

### Core Framework
- **FastAPI 0.115.5** - Modern async Python web framework
- **Uvicorn** - ASGI server with WebSocket support
- **Pydantic 2.10.3** - Data validation and settings management

### Database
- **SQLAlchemy 2.0.36** - ORM for database operations
- **Alembic 1.14.0** - Database migration management
- **PostgreSQL** - Primary database (via psycopg2-binary)

### Authentication & Security
- **PyJWT 2.10.1** - JWT token generation/validation
- **python-jose[cryptography]** - JWT with cryptographic signing
- **passlib[bcrypt]** - Password hashing with bcrypt

### Cloud & Storage
- **boto3** - AWS SDK (S3, Secrets Manager, CloudWatch)
- **Cloudflare R2** - S3-compatible object storage
- **Redis 5.2.0** - Caching layer (optional)

### PDF Generation
- **reportlab 4.2.5** - PDF generation for budgets/renderings
- **Pillow 11.0.0** - Image processing

### AWS Deployment
- **mangum 0.19.0** - ASGI adapter for AWS Lambda
- **aws-xray-sdk** - Distributed tracing
- **watchtower** - CloudWatch log integration

---

## Project Structure

```
canas-construction/
├── app/
│   ├── api/                    # API Routes
│   │   ├── health.py           # Health check endpoints
│   │   ├── routes.py           # Main router configuration
│   │   └── v1/                 # API version 1 endpoints
│   │       ├── auth.py         # Authentication (login, register)
│   │       ├── users.py        # User management
│   │       ├── companies.py    # Company management
│   │       ├── roles.py        # Role management
│   │       ├── clients.py      # Client CRM endpoints
│   │       ├── projects.py     # Project management
│   │       ├── project_categories.py
│   │       ├── catalog_items.py   # Product/service catalog
│   │       ├── visits.py       # Project visits/inspections
│   │       ├── budgets.py      # Budget/quote management
│   │       ├── renderings.py   # 3D rendering proposals
│   │       └── uploads.py      # File upload endpoints
│   │
│   ├── core/                   # Core Infrastructure
│   │   ├── config.py           # Settings and configuration
│   │   ├── database.py         # Database session management
│   │   ├── dependencies.py     # DI container (SERVICE FACTORIES)
│   │   ├── auth.py             # Authentication dependencies
│   │   ├── jwt.py              # JWT token operations
│   │   ├── password.py         # Password hashing utilities
│   │   ├── logging.py          # Structured logging
│   │   ├── exceptions.py       # Custom exception classes
│   │   ├── error_handlers.py   # Global error handlers
│   │   ├── security.py         # Security utilities
│   │   └── cache.py            # Redis caching
│   │
│   ├── models/                 # SQLAlchemy Models
│   │   ├── base.py             # Base model with id, timestamps
│   │   ├── company.py          # Multi-tenant root entity
│   │   ├── user.py             # Users with roles
│   │   ├── role.py             # RBAC roles
│   │   ├── client.py           # Construction clients
│   │   ├── project.py          # Construction projects
│   │   ├── project_category.py # Project types (remodel, new, etc)
│   │   ├── catalog_item.py     # Reusable products/services
│   │   ├── visit.py            # Site visits/inspections
│   │   ├── budget.py           # Budget with line items
│   │   └── rendering.py        # 3D rendering proposals
│   │
│   ├── repositories/           # Data Access Layer
│   │   ├── base.py             # Generic CRUD operations
│   │   ├── company_repository.py
│   │   ├── user_repository.py
│   │   ├── role_repository.py
│   │   ├── client_repository.py
│   │   ├── project_repository.py
│   │   ├── project_category_repository.py
│   │   ├── catalog_item_repository.py
│   │   ├── visit_repository.py
│   │   ├── budget_repository.py
│   │   └── rendering_repository.py
│   │
│   ├── schemas/                # Pydantic Schemas
│   │   ├── auth.py             # Login, token response
│   │   ├── user.py             # UserCreate, UserResponse
│   │   ├── company.py          # CompanyCreate, CompanyResponse
│   │   ├── project.py          # ProjectCreate, ProjectDetailResponse
│   │   ├── budget.py           # BudgetCreate, BudgetResponse
│   │   └── ...                 # One schema file per domain model
│   │
│   ├── services/               # Business Logic Layer
│   │   ├── company_service.py
│   │   ├── user_service.py
│   │   ├── role_service.py
│   │   ├── client_service.py
│   │   ├── project_service.py
│   │   ├── project_category_service.py
│   │   ├── catalog_item_service.py
│   │   ├── visit_service.py
│   │   ├── budget_service.py
│   │   ├── rendering_service.py
│   │   ├── pdf_service.py      # PDF generation
│   │   └── storage_service.py  # File upload (S3/R2)
│   │
│   └── main.py                 # FastAPI app factory
│
├── alembic/                    # Database Migrations
│   └── versions/               # Migration files
│
├── aws/                        # AWS Deployment Config
│   ├── buildspec.yml           # CodeBuild
│   ├── cloudformation-infrastructure.yml
│   └── ecs-task-definition.json
│
├── tests/                      # Unit & Integration Tests
├── scripts/                    # Utility scripts
├── .env.example                # Environment variables template
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Local development
├── alembic.ini                 # Alembic configuration
└── Makefile                    # Common commands
```

---

## Core Patterns & Principles

### 1. **Dependency Injection (DI)**

All services are created via **factory functions** in `core/dependencies.py`:

```python
# ❌ DON'T create services directly in routes
service = ProjectService(repo1, repo2, repo3)  # WRONG

# ✅ DO use dependency injection
@router.get("/projects")
def list_projects(
    service: ProjectService = Depends(get_project_service)  # Injected
):
    return service.get_projects()
```

**Benefits:**
- Easy to mock for testing
- Centralized dependency management
- Loose coupling between layers

### 2. **Repository Pattern**

All database operations go through repositories:

```python
# ❌ DON'T query database directly in services
projects = db.query(Project).filter(Project.company_id == company_id).all()

# ✅ DO use repository methods
projects = self.project_repository.get_all(
    filters={"company_id": company_id}
)
```

**Base Repository provides:**
- `create(**kwargs)` - Create record
- `get_by_id(id)` - Get by ID
- `get_by_id_or_fail(id)` - Get or raise 404
- `get_all(skip, limit, filters, order_by)` - List with pagination
- `update(instance, **kwargs)` - Update record
- `delete(instance)` - Delete record
- `exists(**filters)` - Check existence
- `count(filters)` - Count records
- `bulk_create(objects)` - Bulk insert

### 3. **Service Layer (Business Logic)**

Services contain all business rules and validations:

```python
class ProjectService:
    def create_project(self, data: ProjectCreate, company_id: UUID):
        # Business rule: validate client belongs to company
        client = self.client_repository.get_by_id(data.client_id)
        if client.company_id != company_id:
            raise ValidationException("Client doesn't belong to company")
        
        # Business rule: validate category exists
        category = self.category_repository.get_by_id(data.category_id)
        if not category:
            raise NotFoundException("Category", data.category_id)
        
        # Create project
        return self.project_repository.create(**data.dict())
```

**Service responsibilities:**
- ✅ Business rule validation
- ✅ Cross-entity validation
- ✅ Complex calculations
- ✅ Orchestrating multiple repositories
- ❌ HTTP concerns (handled by routes)
- ❌ Direct database queries (handled by repositories)

### 4. **N+1 Query Optimization**

Use eager loading to avoid N+1 query problems:

```python
# ❌ SLOW: N+1 queries (1 + N additional queries)
projects = db.query(Project).filter(...).all()
for project in projects:
    print(project.client.name)  # Additional query per project!

# ✅ FAST: 1-2 queries total
from sqlalchemy.orm import joinedload

projects = db.query(Project)\
    .options(joinedload(Project.client))\
    .options(joinedload(Project.category))\
    .filter(...).all()

for project in projects:
    print(project.client.name)  # No additional query!
```

### 5. **Multi-Tenant Isolation**

**Every query MUST filter by `company_id`:**

```python
# ❌ SECURITY RISK: No company filter
projects = self.repository.get_all()

# ✅ SECURE: Always filter by company
projects = self.repository.get_all(
    filters={"company_id": company_id}
)
```

**Company-scoped entities:**
- Users
- Roles
- Clients
- Projects
- Project Categories
- Catalog Items
- Visits (via Project → Client → Company)
- Budgets (via Visit → Project → Client → Company)

---

## Database Models & Relationships

### Base Model (Inherited by all models)

```python
class BaseModel(Base):
    __abstract__ = True
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

**All models use UUID primary keys, not integers.**

### Entity Relationships

```
Company (Multi-Tenant Root)
├── Users (many-to-one)
│   └── Roles (many-to-many via user_roles table)
├── Clients (many-to-one)
│   └── Projects (many-to-one)
│       ├── Project Category (many-to-one)
│       ├── Created By User (many-to-one, audit trail)
│       └── Visits (one-to-many)
│           ├── Budget (one-to-one)
│           │   └── Budget Items (one-to-many)
│           │       └── Catalog Item (optional, many-to-one)
│           └── Renderings (many-to-one, optional)
│               ├── Rendering Images (one-to-many)
│               └── Rendering Items (one-to-many)
└── Catalog Items (many-to-one)
    └── Created By User (many-to-one, audit trail)
```

### Key Models

#### **Company** (Multi-Tenant Root)
```python
class Company(BaseModel):
    name = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(50))
    address = Column(String(500))
    is_active = Column(Boolean, default=True)
```

#### **User**
```python
class User(BaseModel):
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(50))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    company_id = Column(UUID, ForeignKey("companies.id"), nullable=False)
    
    # Many-to-many with Role
    roles = relationship("Role", secondary=user_roles, back_populates="users")
```

#### **Client**
```python
class Client(BaseModel):
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    company_id = Column(UUID, ForeignKey("companies.id"), nullable=False)
```

#### **Project**
```python
class ProjectStatus(enum.Enum):
    LEAD = "lead"
    QUOTED = "quoted"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"

class Project(BaseModel):
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.LEAD)
    
    # Financial
    estimated_budget = Column(Numeric(12, 2))
    actual_cost = Column(Numeric(12, 2))
    
    # Dates
    start_date = Column(Date)
    estimated_completion_date = Column(Date)
    actual_completion_date = Column(Date)
    
    # Location
    address = Column(String(500))
    
    # Foreign keys
    client_id = Column(UUID, ForeignKey("clients.id"), nullable=False)
    category_id = Column(UUID, ForeignKey("project_categories.id"), nullable=False)
    created_by_user_id = Column(UUID, ForeignKey("users.id"))  # Audit trail
```

#### **Visit** (Principal Process Container)
```python
class VisitStatus(enum.Enum):
    PLANNING = "planning"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    INSPECTION_REQUIRED = "inspection_required"
    VISITED = "visited"

class Visit(BaseModel):
    """
    This is the PRINCIPAL CONTAINER for the construction project process.
    Users create visits to gather information, add images, and record details.
    Engineers review and change status, edit info, or add items/prices.
    """
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(VisitStatus), default=VisitStatus.PLANNING)
    
    visit_date = Column(Date)
    inspection_notes = Column(Text)
    
    # Financial estimates from visit
    estimated_materials_cost = Column(Numeric(12, 2))
    estimated_labor_cost = Column(Numeric(12, 2))
    estimated_total_cost = Column(Numeric(12, 2))
    
    # Images (JSON array of URLs)
    images = Column(JSON)  # ["url1", "url2", ...]
    
    project_id = Column(UUID, ForeignKey("projects.id"), nullable=False)
    created_by_user_id = Column(UUID, ForeignKey("users.id"))
```

#### **Budget** (One-to-One with Visit)
```python
class BudgetStatus(enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVISED = "revised"

class Budget(BaseModel):
    """
    Budget for project cost breakdown.
    When status becomes ACCEPTED, project status changes to APPROVED.
    """
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(BudgetStatus), default=BudgetStatus.DRAFT)
    total_amount = Column(Numeric(12, 2), default=0)
    
    visit_id = Column(UUID, ForeignKey("visits.id"), unique=True, nullable=False)
```

#### **Catalog Item** (Reusable Products/Services)
```python
class UnitType(enum.Enum):
    POUND = "pound"
    SQUARE_FOOT = "square_foot"
    FOOT = "foot"
    CUBIC_YARD = "cubic_yard"
    EACH = "each"
    HOUR = "hour"
    DAY = "day"

class CatalogItem(BaseModel):
    name = Column(String(255), nullable=False)
    description = Column(Text)
    unity = Column(Enum(UnitType), nullable=False)
    price_base = Column(Numeric(12, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    
    company_id = Column(UUID, ForeignKey("companies.id"), nullable=False)
    created_by_user_id = Column(UUID, ForeignKey("users.id"))
```

#### **Rendering** (Visual Proposals)
```python
class RenderingStatus(enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    APPROVED = "approved"
    REJECTED = "rejected"

class Rendering(BaseModel):
    """
    Visual proposal with 3D renders, material samples, and item details.
    Can be generated as PDF for client presentation.
    """
    title = Column(String(255), nullable=False)
    description = Column(Text)
    notes = Column(Text)
    expiration_date = Column(Date)
    status = Column(Enum(RenderingStatus), default=RenderingStatus.DRAFT)
    total_amount = Column(Numeric(12, 2), default=0)
    
    visit_id = Column(UUID, ForeignKey("visits.id"))  # Optional
```

---

## Business Logic Flow

### 1. **Project Lifecycle**

```mermaid
graph LR
    A[Lead] --> B[Quoted]
    B --> C[Approved]
    C --> D[In Progress]
    D --> E[Completed]
    
    B -.-> F[Cancelled]
    C -.-> F
    D -.-> G[On Hold]
    G -.-> D
```

**Status Flow:**
1. **LEAD** - Initial prospect
2. **QUOTED** - Budget sent to client
3. **APPROVED** - Client accepted budget
4. **IN_PROGRESS** - Work started
5. **COMPLETED** - Project finished
6. **CANCELLED** - Project cancelled
7. **ON_HOLD** - Temporarily paused

### 2. **Visit & Budget Workflow**

```
1. Create Project (status: LEAD)
2. Create Visit for Project (status: PLANNING)
3. Add visit details, photos, notes
4. Engineer reviews (status: IN_REVIEW → VISITED)
5. Create Budget for Visit (status: DRAFT)
6. Add Budget Items (from Catalog or custom)
7. Send Budget to Client (status: PENDING_APPROVAL)
8. Client Decision:
   ├─ ACCEPTED → Project status: APPROVED
   └─ REJECTED → Budget status: REJECTED → Create revised budget
```

### 3. **Rendering Workflow**

```
1. Create Rendering (optional, for Visit)
2. Upload 3D rendered images
3. Add material samples with images
4. Add rendering items with specs/pricing
5. Generate PDF
6. Send to Client (status: SENT)
7. Client Decision:
   ├─ APPROVED → Can proceed with budget
   └─ REJECTED → Revise rendering
```

---

## Authentication & Authorization

### JWT Token-Based Authentication

**Login Flow:**
1. POST `/api/v1/auth/login` with email/password
2. Server validates credentials
3. Returns JWT access token
4. Client includes token in `Authorization: Bearer {token}` header

**Token Structure:**
```json
{
  "sub": "user-uuid",
  "company_id": "company-uuid",
  "email": "user@example.com",
  "exp": 1234567890
}
```

### Protecting Endpoints

```python
from app.core.auth import get_current_user, get_current_active_user

# Require authentication
@router.get("/protected")
def protected_route(
    current_user: User = Depends(get_current_user)
):
    return {"user_id": current_user.id}

# Require active user
@router.get("/active-only")
def active_only_route(
    current_user: User = Depends(get_current_active_user)
):
    return {"user_id": current_user.id}
```

### Current Authentication Status

⚠️ **NOTE:** Most endpoints currently have authentication **commented out** in `api/routes.py`:

```python
# TODO: Add authentication to these endpoints using Depends(get_current_active_user)
api_router.include_router(companies.router)
api_router.include_router(roles.router)
# ...
```

**To enable authentication:**
1. Add `dependencies=[Depends(get_current_active_user)]` to router
2. OR add to individual route functions

---

## API Endpoints Structure

### Health Checks
- `GET /api/v1/health` - Basic health check (ALB target)
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/health/live` - Liveness probe

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login (returns JWT)

### Companies
- `POST /api/v1/companies` - Create company
- `GET /api/v1/companies` - List companies
- `GET /api/v1/companies/{id}` - Get company
- `PUT /api/v1/companies/{id}` - Update company
- `DELETE /api/v1/companies/{id}` - Delete company

### Users
- `POST /api/v1/users` - Create user
- `GET /api/v1/users?company_id={uuid}` - List users
- `GET /api/v1/users/{id}` - Get user
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user
- `POST /api/v1/users/{id}/roles` - Assign roles to user

### Clients (CRM)
- `POST /api/v1/clients` - Create client
- `GET /api/v1/clients?company_id={uuid}` - List clients
- `GET /api/v1/clients/{id}` - Get client
- `PUT /api/v1/clients/{id}` - Update client
- `DELETE /api/v1/clients/{id}` - Delete client

### Projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects?company_id={uuid}&status={status}` - List projects
- `GET /api/v1/projects/{id}` - Get project details
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Visits
- `POST /api/v1/visits` - Create visit
- `GET /api/v1/visits?project_id={uuid}` - List visits
- `GET /api/v1/visits/{id}` - Get visit
- `PUT /api/v1/visits/{id}` - Update visit
- `DELETE /api/v1/visits/{id}` - Delete visit

### Budgets
- `POST /api/v1/budgets` - Create budget
- `GET /api/v1/budgets?visit_id={uuid}` - List budgets
- `GET /api/v1/budgets/{id}` - Get budget with items
- `PUT /api/v1/budgets/{id}` - Update budget
- `DELETE /api/v1/budgets/{id}` - Delete budget
- `POST /api/v1/budgets/{id}/items` - Add budget item
- `GET /api/v1/budgets/{id}/pdf` - Generate PDF

### Catalog Items
- `POST /api/v1/catalog-items` - Create catalog item
- `GET /api/v1/catalog-items?company_id={uuid}` - List items
- `GET /api/v1/catalog-items/{id}` - Get item
- `PUT /api/v1/catalog-items/{id}` - Update item
- `DELETE /api/v1/catalog-items/{id}` - Delete item

### Renderings
- `POST /api/v1/renderings` - Create rendering
- `GET /api/v1/renderings?visit_id={uuid}` - List renderings
- `GET /api/v1/renderings/{id}` - Get rendering
- `PUT /api/v1/renderings/{id}` - Update rendering
- `DELETE /api/v1/renderings/{id}` - Delete rendering
- `POST /api/v1/renderings/{id}/images` - Upload rendering image
- `GET /api/v1/renderings/{id}/pdf` - Generate PDF

### File Uploads
- `POST /api/v1/uploads/image` - Upload image (S3/R2)

---

## Multi-Tenant Architecture

### Principles

**Every API request MUST include `company_id` for data isolation.**

### Query Patterns

```python
# ✅ CORRECT: Filter by company_id
@router.get("/clients")
def list_clients(
    company_id: UUID = Query(..., description="REQUIRED for multi-tenant isolation"),
    service: ClientService = Depends(get_client_service)
):
    return service.get_clients(company_id=company_id)

# ❌ WRONG: No company filter (security risk!)
@router.get("/clients")
def list_clients(service: ClientService = Depends(get_client_service)):
    return service.get_clients()  # Returns ALL clients from ALL companies!
```

### Service Layer Validation

```python
def create_project(self, data: ProjectCreate, company_id: UUID):
    # Validate client belongs to company
    client = self.client_repository.get_by_id(data.client_id)
    if client.company_id != company_id:
        raise ValidationException("Client doesn't belong to company")
    
    # Validate category belongs to company
    category = self.category_repository.get_by_id(data.category_id)
    if category.company_id != company_id:
        raise ValidationException("Category doesn't belong to company")
    
    # Create project
    return self.project_repository.create(...)
```

### Audit Trail

Track user actions with `created_by_user_id`:

```python
# Projects track creator
project.created_by_user_id = current_user.id

# Catalog items track creator
catalog_item.created_by_user_id = current_user.id

# Visits track creator
visit.created_by_user_id = current_user.id
```

---

## Development Guidelines

### 1. **Adding a New Endpoint**

**Step-by-step:**

1. **Create/Update Model** (`app/models/`)
   ```python
   class NewEntity(BaseModel):
       __tablename__ = "new_entities"
       name = Column(String(255), nullable=False)
       company_id = Column(UUID, ForeignKey("companies.id"))
   ```

2. **Create Migration**
   ```bash
   alembic revision --autogenerate -m "Add new_entities table"
   alembic upgrade head
   ```

3. **Create Schema** (`app/schemas/`)
   ```python
   class NewEntityCreate(BaseModel):
       name: str
   
   class NewEntityResponse(BaseModel):
       id: UUID
       name: str
       created_at: datetime
       
       class Config:
           from_attributes = True
   ```

4. **Create Repository** (`app/repositories/`)
   ```python
   class NewEntityRepository(BaseRepository[NewEntity]):
       def __init__(self, db: Session):
           super().__init__(NewEntity, db)
   ```

5. **Create Service** (`app/services/`)
   ```python
   class NewEntityService:
       def __init__(self, repository: NewEntityRepository):
           self.repository = repository
       
       def create(self, data: NewEntityCreate, company_id: UUID):
           return self.repository.create(
               name=data.name,
               company_id=company_id
           )
   ```

6. **Add DI Factory** (`app/core/dependencies.py`)
   ```python
   def get_new_entity_service(db: Session = Depends(get_db)):
       repo = NewEntityRepository(db)
       return NewEntityService(repository=repo)
   ```

7. **Create Route** (`app/api/v1/new_entities.py`)
   ```python
   router = APIRouter(prefix="/new-entities", tags=["New Entities"])
   
   @router.post("/", response_model=NewEntityResponse)
   def create_new_entity(
       data: NewEntityCreate,
       company_id: UUID = Query(...),
       service: NewEntityService = Depends(get_new_entity_service)
   ):
       return service.create(data, company_id)
   ```

8. **Register Route** (`app/api/routes.py`)
   ```python
   from app.api.v1 import new_entities
   api_router.include_router(new_entities.router)
   ```

### 2. **Code Style**

**Follow these conventions:**

- ✅ Use type hints everywhere
- ✅ Document complex business logic
- ✅ Use Pydantic schemas for validation
- ✅ Services return ORM models, routes convert to schemas
- ✅ Use `UUID` for IDs, not `str` or `int`
- ✅ Use `Query(...)` for required query params
- ✅ Use `Query(None)` for optional query params
- ❌ Don't query database in routes
- ❌ Don't put business logic in repositories
- ❌ Don't return raw dictionaries from services

### 3. **Error Handling**

Use custom exceptions:

```python
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    AuthenticationException,
    DatabaseException
)

# Not found
if not user:
    raise NotFoundException("User", user_id)

# Validation error
if client.company_id != company_id:
    raise ValidationException("Client doesn't belong to company")

# Auth error
if not verify_password(password, user.hashed_password):
    raise AuthenticationException("Invalid credentials")
```

### 4. **Transaction Management**

**Repositories use `flush()`, not `commit()`:**

```python
# In repository
def create(self, **kwargs):
    instance = self.model(**kwargs)
    self.db.add(instance)
    self.db.flush()  # ← Not commit!
    self.db.refresh(instance)
    return instance
```

**`get_db()` dependency handles commit/rollback:**

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()  # ← Auto-commit if no exception
    except Exception:
        db.rollback()  # ← Auto-rollback on error
        raise
    finally:
        db.close()
```

### 5. **Testing**

```bash
# Run all tests
make test

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/test_projects.py -v
```

**Test structure:**
```python
def test_create_project(db_session):
    # Arrange
    company = create_test_company(db_session)
    client = create_test_client(db_session, company.id)
    
    # Act
    project = create_project(client_id=client.id)
    
    # Assert
    assert project.client_id == client.id
    assert project.status == ProjectStatus.LEAD
```

---

## Common Operations

### 1. **Database Migrations**

```bash
# Create new migration
alembic revision --autogenerate -m "Add new column"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

### 2. **Local Development**

```bash
# Install dependencies
make dev-install

# Run development server
make run
# OR
uvicorn app.main:app --reload

# View API docs
open http://localhost:8000/api/v1/docs
```

### 3. **Docker Development**

```bash
# Build image
make docker-build

# Run with Docker Compose
docker-compose up

# Stop containers
docker-compose down

# View logs
docker-compose logs -f
```

### 4. **Environment Variables**

Copy `.env.example` to `.env`:

```bash
# Application
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/canas_construction

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

# AWS (optional)
AWS_REGION=us-east-1
S3_BUCKET_NAME=canas-construction-files

# Cloudflare R2 (optional)
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=canas-construction
```

---

## Deployment & AWS

### AWS Deployment Options

1. **ECS Fargate** (Recommended) - Serverless containers
2. **Lambda + API Gateway** - Fully serverless (uses Mangum adapter)
3. **Elastic Beanstalk** - Managed platform
4. **EC2** - Traditional compute

### ECS Fargate Deployment

```bash
# 1. Create infrastructure (VPC, RDS, ElastiCache, ECR)
aws cloudformation create-stack \
  --stack-name canas-construction \
  --template-body file://aws/cloudformation-infrastructure.yml \
  --capabilities CAPABILITY_IAM

# 2. Build and push Docker image
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1

make docker-build
make aws-ecr-login
make aws-push

# 3. Create secrets
aws secretsmanager create-secret \
  --name canas-construction/database-url \
  --secret-string "postgresql://..."

aws secretsmanager create-secret \
  --name canas-construction/secret-key \
  --secret-string "your-secret-key"

# 4. Register task definition
aws ecs register-task-definition \
  --cli-input-json file://aws/ecs-task-definition.json

# 5. Create ECS service
aws ecs create-service \
  --cluster production-cluster \
  --service-name canas-construction-api \
  --task-definition canas-construction-api \
  --desired-count 2 \
  --launch-type FARGATE
```

### Lambda Deployment

The app includes Mangum handler for Lambda:

```python
# app/main.py
from mangum import Mangum
handler = Mangum(app, lifespan="off")
```

Package for Lambda:
```bash
mkdir package
pip install -r requirements.txt -t package/
cp -r app package/
cd package && zip -r ../deployment.zip .
```

### CloudWatch Logging

Logs are structured JSON for easy parsing:

```json
{
  "timestamp": "2025-02-03T10:30:00Z",
  "level": "INFO",
  "message": "Created project",
  "project_id": "uuid",
  "company_id": "uuid",
  "user_id": "uuid"
}
```

View logs:
```bash
aws logs tail /ecs/canas-construction-api --follow
```

---

## Key Takeaways

### ✅ DO
- Use dependency injection for all services
- Filter by `company_id` for multi-tenant isolation
- Use eager loading (`joinedload`) to avoid N+1 queries
- Validate cross-entity relationships in services
- Use custom exceptions for error handling
- Use UUIDs for primary keys
- Track audit trails with `created_by_user_id`
- Write tests for business logic

### ❌ DON'T
- Query database directly in routes
- Put business logic in repositories
- Return raw dictionaries from services
- Skip company_id validation
- Use `commit()` in repositories (use `flush()`)
- Mix authentication logic with business logic
- Hardcode configuration values

---

## Questions or Issues?

### Common Pitfalls

**Q: Getting N+1 query performance issues?**
A: Use `joinedload()` in repository queries.

**Q: Multi-tenant isolation not working?**
A: Ensure all queries filter by `company_id`.

**Q: Authentication not working?**
A: Check if endpoints have authentication enabled in `api/routes.py`.

**Q: Database transaction rollback?**
A: Let `get_db()` handle transactions. Don't commit in repositories.

**Q: CORS errors?**
A: Update `CORS_ORIGINS` in `.env` to include frontend URL.

---

**Last Updated:** February 3, 2025
**Version:** 1.0.0
**Architecture:** Clean Architecture + SOLID + Repository Pattern + DI
