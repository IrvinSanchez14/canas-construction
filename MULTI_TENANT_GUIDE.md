# Multi-Tenant Architecture Guide

## Overview
This project uses a multi-tenant architecture where each company has isolated data with its own users and roles.

## Database Schema

### Tables

1. **companies** - Stores different companies/tenants
   - `id`, `name`, `email`, `phone`, `address`, `is_active`
   - `created_at`, `updated_at`

2. **users** - Stores users belonging to a company
   - `id`, `email`, `username`, `hashed_password`
   - `first_name`, `last_name`, `phone`
   - `is_active`, `is_superuser`
   - `company_id` (FK to companies)
   - `created_at`, `updated_at`

3. **roles** - Stores roles per company
   - `id`, `name`, `description`, `is_active`
   - `company_id` (FK to companies)
   - `created_at`, `updated_at`

4. **user_roles** - Many-to-many relationship between users and roles
   - `user_id` (FK to users)
   - `role_id` (FK to roles)

## Key Features

### Data Isolation
- Each user belongs to ONE company (`company_id` FK)
- Each role belongs to ONE company (`company_id` FK)
- Cascade deletes: If a company is deleted, all its users and roles are deleted

### Relationships
- **Company → Users**: One-to-Many
- **Company → Roles**: One-to-Many
- **User → Roles**: Many-to-Many (through `user_roles` table)

## Usage Examples

### Creating a New Company
```python
from sqlalchemy.orm import Session
from app.models import Company

def create_company(db: Session, name: str, email: str):
    company = Company(
        name=name,
        email=email,
        phone="555-1234",
        address="123 Main St"
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company
```

### Creating a User for a Company
```python
from app.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user(db: Session, company_id: int, email: str, password: str):
    hashed_password = pwd_context.hash(password)
    user = User(
        email=email,
        username=email.split("@")[0],
        hashed_password=hashed_password,
        first_name="John",
        last_name="Doe",
        company_id=company_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

### Creating a Role for a Company
```python
from app.models import Role

def create_role(db: Session, company_id: int, name: str):
    role = Role(
        name=name,
        description=f"Role for {name}",
        company_id=company_id
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role
```

### Assigning Roles to a User
```python
def assign_role_to_user(db: Session, user_id: int, role_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    role = db.query(Role).filter(Role.id == role_id).first()

    # Make sure user and role belong to the same company!
    if user.company_id != role.company_id:
        raise ValueError("User and role must belong to the same company")

    user.roles.append(role)
    db.commit()
    return user
```

### Querying Users by Company (Data Isolation)
```python
def get_company_users(db: Session, company_id: int):
    # Always filter by company_id to ensure data isolation
    return db.query(User).filter(User.company_id == company_id).all()
```

### Getting User with Roles
```python
def get_user_with_roles(db: Session, user_id: int, company_id: int):
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == company_id  # Always filter by company!
    ).first()

    # Access roles through relationship
    if user:
        print(f"User: {user.full_name}")
        print(f"Roles: {[role.name for role in user.roles]}")

    return user
```

## Migration Commands

### Create a new migration
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Run migrations (upgrade database)
```bash
alembic upgrade head
```

### Rollback last migration
```bash
alembic downgrade -1
```

### Check current migration version
```bash
alembic current
```

### View migration history
```bash
alembic history
```

## Security Best Practices

1. **Always filter by company_id**: Every query should filter by the company to ensure data isolation
2. **Validate company ownership**: Before any operation, verify that the user belongs to the company
3. **Use dependency injection**: Create a FastAPI dependency to get the current user's company_id

### Example: FastAPI Dependency for Company Isolation
```python
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db

async def get_current_company_id(
    current_user: User = Depends(get_current_user),
) -> int:
    """Get the company_id of the current authenticated user."""
    return current_user.company_id

@app.get("/users")
def list_users(
    company_id: int = Depends(get_current_company_id),
    db: Session = Depends(get_db)
):
    # This automatically filters by the user's company
    return db.query(User).filter(User.company_id == company_id).all()
```

## Next Steps

1. Run the migration: `alembic upgrade head`
2. Create Pydantic schemas for API input/output
3. Create CRUD operations in `app/services/`
4. Create API endpoints in `app/api/`
5. Add authentication and authorization logic
6. Create middleware to automatically filter queries by company
