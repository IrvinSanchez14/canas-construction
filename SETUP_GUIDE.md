# Setup Guide - Multi-Tenant API

## Prerequisites

- Python 3.11+
- PostgreSQL database
- Virtual environment activated

## Installation Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Edit your `.env` file with the database connection:

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/canas_construction

# Security
SECRET_KEY=your-secret-key-here-change-in-production

# Application
DEBUG=True
ENVIRONMENT=development
```

### 3. Run Database Migrations

```bash
# Activate virtual environment
source venv/bin/activate

# Run migrations to create tables
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 8015a87589a3, Create initial tables: company, role, user
```

### 4. Start the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 5. Verify Installation

Visit the API documentation:
```
http://localhost:8000/docs
```

You should see:
- Health endpoints
- Companies endpoints
- Roles endpoints
- Users endpoints

### 6. Test the API

Run the test script:
```bash
python test_api.py
```

This will:
1. Create a company
2. Create 3 roles (Administrator, Project Manager, Field Worker)
3. Create 3 users with different roles
4. Test login functionality
5. Test CRUD operations

## Quick Start - Manual Testing

### 1. Create a Company

```bash
curl -X POST http://localhost:8000/api/v1/companies/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Construction Company",
    "email": "info@mycompany.com",
    "phone": "555-1234",
    "address": "123 Main St"
  }'
```

Save the returned `id` (e.g., `company_id = 1`)

### 2. Create a Role

```bash
curl -X POST http://localhost:8000/api/v1/roles/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Administrator",
    "description": "Full access",
    "company_id": 1
  }'
```

Save the returned `id` (e.g., `role_id = 1`)

### 3. Create a User

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@mycompany.com",
    "username": "admin",
    "password": "SecurePass123!",
    "first_name": "Admin",
    "last_name": "User",
    "company_id": 1,
    "role_ids": [1]
  }'
```

### 4. Login

```bash
curl -X POST http://localhost:8000/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@mycompany.com",
    "password": "SecurePass123!"
  }'
```

## Project Structure

```
app/
├── api/
│   ├── v1/
│   │   ├── companies.py    # Company endpoints
│   │   ├── roles.py        # Role endpoints
│   │   └── users.py        # User endpoints
│   ├── health.py           # Health check
│   └── routes.py           # Main router
├── core/
│   ├── config.py           # Configuration
│   ├── database.py         # Database session
│   ├── logging.py          # Logging setup
│   └── security.py         # Security utilities
├── models/
│   ├── base.py             # Base model
│   ├── company.py          # Company model
│   ├── role.py             # Role model
│   └── user.py             # User model
├── schemas/
│   ├── company.py          # Company schemas
│   ├── role.py             # Role schemas
│   └── user.py             # User schemas
├── services/
│   ├── company_service.py  # Company business logic
│   ├── role_service.py     # Role business logic
│   └── user_service.py     # User business logic
└── main.py                 # FastAPI application

alembic/
└── versions/               # Database migrations
```

## Database Schema

```
companies
├── id (PK)
├── name (unique)
├── email (unique)
├── phone
├── address
├── is_active
├── created_at
└── updated_at

users
├── id (PK)
├── email (unique)
├── username
├── hashed_password
├── first_name
├── last_name
├── phone
├── is_active
├── is_superuser
├── company_id (FK → companies)
├── created_at
└── updated_at

roles
├── id (PK)
├── name
├── description
├── is_active
├── company_id (FK → companies)
├── created_at
└── updated_at

user_roles (association table)
├── user_id (FK → users)
└── role_id (FK → roles)
```

## Available Endpoints

### Health
- `GET /api/v1/health` - Health check

### Companies
- `POST /api/v1/companies/` - Create company
- `GET /api/v1/companies/` - List companies
- `GET /api/v1/companies/{id}` - Get company
- `PUT /api/v1/companies/{id}` - Update company
- `DELETE /api/v1/companies/{id}` - Delete company

### Roles
- `POST /api/v1/roles/` - Create role
- `GET /api/v1/roles/` - List roles
- `GET /api/v1/roles/{id}` - Get role
- `PUT /api/v1/roles/{id}` - Update role
- `DELETE /api/v1/roles/{id}` - Delete role

### Users
- `POST /api/v1/users/` - Create user
- `GET /api/v1/users/` - List users
- `GET /api/v1/users/{id}` - Get user
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user
- `POST /api/v1/users/login` - Login

## Development Commands

### Create a new migration
```bash
alembic revision --autogenerate -m "Description"
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback migration
```bash
alembic downgrade -1
```

### Check current migration
```bash
alembic current
```

### View migration history
```bash
alembic history
```

## Troubleshooting

### Migration errors
If you get migration errors, try:
```bash
# Drop all tables and start fresh (DEVELOPMENT ONLY!)
alembic downgrade base
alembic upgrade head
```

### Import errors
Make sure you're in the project root and the virtual environment is activated:
```bash
source venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Database connection errors
Verify your `.env` file has the correct `DATABASE_URL`:
```bash
DATABASE_URL=postgresql://username:password@host:port/database
```

Test connection:
```bash
psql postgresql://username:password@host:port/database
```

## Next Steps

1. ✅ Tables created (Company, Role, User)
2. ✅ CRUD endpoints implemented
3. ✅ Business logic in service layer
4. ✅ Multi-tenant architecture with data isolation
5. 🔲 Add JWT authentication (recommended)
6. 🔲 Add authorization middleware
7. 🔲 Add automated tests
8. 🔲 Add frontend application

## Additional Resources

- **API Documentation**: See `API_DOCUMENTATION.md`
- **Multi-Tenant Guide**: See `MULTI_TENANT_GUIDE.md`
- **Interactive API Docs**: http://localhost:8000/docs
