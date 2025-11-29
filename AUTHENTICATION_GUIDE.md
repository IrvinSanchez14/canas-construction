# 🔐 Authentication Guide - JWT Implementation

Complete guide for implementing and using JWT authentication in your Construction CRM API.

## 📋 Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Authentication Flow](#authentication-flow)
- [Protecting Endpoints](#protecting-endpoints)
- [API Usage Examples](#api-usage-examples)
- [Security Best Practices](#security-best-practices)

---

## Overview

### ✅ What's Implemented

**JWT Authentication System** with:
- **Access Tokens**: Expire in 1 day (86400 seconds)
- **Refresh Tokens**: Expire in 30 days
- **Multi-tenant isolation**: Company ID embedded in tokens
- **Role-based access**: User roles and permissions
- **Secure password hashing**: Using bcrypt

### 🔓 Public Endpoints (No Auth Required)

These endpoints do NOT require authentication:
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/setup` - Initial company setup

### 🔒 Protected Endpoints (Auth Required)

All other endpoints require a valid JWT access token in the Authorization header.

---

## Quick Start

### 1. Initial Setup - Create Company & Admin User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/setup" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "ABC Construction",
    "company_email": "admin@abc-construction.com",
    "company_phone": "555-0100",
    "company_address": "123 Main St, City, State",
    "admin_email": "admin@abc-construction.com",
    "admin_username": "admin",
    "admin_password": "SecurePassword123!",
    "admin_first_name": "John",
    "admin_last_name": "Doe",
    "admin_phone": "555-0101"
  }'
```

**Response:**
```json
{
  "company_id": "uuid-here",
  "company_name": "ABC Construction",
  "admin_user_id": "uuid-here",
  "admin_email": "admin@abc-construction.com",
  "message": "Company and admin user created successfully. You can now login with the admin credentials."
}
```

### 2. Login - Get Access Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@abc-construction.com",
    "password": "SecurePassword123!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 3. Use Access Token in Requests

```bash
curl -X GET "http://localhost:8000/api/v1/clients/?company_id=your-company-uuid" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 4. Refresh Token When Expired

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

---

## Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Database

    Note over Client,Database: Initial Setup
    Client->>API: POST /auth/setup (company + admin)
    API->>Database: Create company + admin user
    Database-->>API: Company & User created
    API-->>Client: Setup successful

    Note over Client,Database: Login
    Client->>API: POST /auth/login (email, password)
    API->>Database: Verify credentials
    Database-->>API: User found
    API-->>Client: access_token + refresh_token

    Note over Client,Database: Protected Request
    Client->>API: GET /clients (with Authorization header)
    API->>API: Verify JWT token
    API->>Database: Fetch data
    Database-->>API: Data
    API-->>Client: Protected data

    Note over Client,Database: Token Refresh
    Client->>API: POST /auth/refresh (refresh_token)
    API->>API: Verify refresh token
    API-->>Client: New access_token + refresh_token
```

---

## Protecting Endpoints

### How to Add Authentication to Endpoints

**Step 1:** Import the authentication dependency

```python
from app.core.auth import get_current_active_user
from app.models import User
```

**Step 2:** Add dependency to endpoint

```python
@router.get("/", response_model=List[ClientResponse])
def list_clients(
    company_id: UUID = Query(..., description="Filter by company ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),  # 👈 ADD THIS
    service: ClientService = Depends(get_client_service)
):
    """Get all clients for a company."""
    # Automatically validates token and gets user
    # Use current_user to access user info
    return service.get_clients(company_id, skip, limit)
```

### Available Authentication Dependencies

```python
from app.core.auth import (
    get_current_user,          # Get authenticated user (active or inactive)
    get_current_active_user,   # Get active user only (RECOMMENDED)
    get_current_superuser,     # Get superuser only
    get_company_from_token     # Get company ID from token
)
```

### Example: Protecting All Client Endpoints

```python
# app/api/v1/clients.py

from app.core.auth import get_current_active_user
from app.models import User

@router.post("/", response_model=ClientResponse)
def create_client(
    client: ClientCreate,
    current_user: User = Depends(get_current_active_user),  # 🔒 Protected
    service: ClientService = Depends(get_client_service)
):
    """Create client - requires authentication."""
    return service.create_client(client)


@router.get("/", response_model=List[ClientResponse])
def list_clients(
    company_id: UUID = Query(...),
    current_user: User = Depends(get_current_active_user),  # 🔒 Protected
    service: ClientService = Depends(get_client_service)
):
    """List clients - requires authentication."""
    # Option: Enforce user can only see their own company's data
    if company_id != current_user.company_id:
        raise HTTPException(403, "Access denied to other company data")

    return service.get_clients(company_id)
```

### Example: Superuser-Only Endpoint

```python
from app.core.auth import get_current_superuser

@router.delete("/companies/{company_id}")
def delete_company(
    company_id: UUID,
    current_user: User = Depends(get_current_superuser),  # 🔒 Superuser only
    service: CompanyService = Depends(get_company_service)
):
    """Delete company - superuser only."""
    service.delete_company(company_id)
```

---

## API Usage Examples

### Using cURL

```bash
# 1. Login
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@abc.com","password":"pass123"}' \
  | jq -r '.access_token')

# 2. Use token in requests
curl -X GET "http://localhost:8000/api/v1/clients/?company_id=uuid" \
  -H "Authorization: Bearer $TOKEN"

# 3. Create resource
curl -X POST "http://localhost:8000/api/v1/clients/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@example.com","company_id":"uuid"}'
```

### Using Python Requests

```python
import requests

# 1. Login
login_response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "admin@abc.com", "password": "pass123"}
)
tokens = login_response.json()
access_token = tokens["access_token"]

# 2. Use token in headers
headers = {"Authorization": f"Bearer {access_token}"}

# 3. Make authenticated requests
clients = requests.get(
    "http://localhost:8000/api/v1/clients/",
    headers=headers,
    params={"company_id": "your-uuid"}
)

print(clients.json())
```

### Using JavaScript/Fetch

```javascript
// 1. Login
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'admin@abc.com',
    password: 'pass123'
  })
});

const { access_token } = await loginResponse.json();

// 2. Use token in subsequent requests
const clientsResponse = await fetch(
  'http://localhost:8000/api/v1/clients/?company_id=uuid',
  {
    headers: { 'Authorization': `Bearer ${access_token}` }
  }
);

const clients = await clientsResponse.json();
```

---

## Security Best Practices

### ⚠️ IMPORTANT for Production

1. **Change SECRET_KEY**
   ```python
   # In app/core/jwt.py - CHANGE THIS!
   # Use environment variable:
   SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-key-for-dev")
   ```

2. **Use Environment Variables**
   ```bash
   # .env file
   JWT_SECRET_KEY=your-super-secret-key-generate-with-openssl
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_DAYS=1
   REFRESH_TOKEN_EXPIRE_DAYS=30
   ```

3. **Generate Secure Secret Key**
   ```bash
   openssl rand -hex 32
   ```

4. **Disable/Protect Setup Endpoint**
   ```python
   # Option 1: Disable after initial setup
   # Option 2: Require setup token
   # Option 3: Only allow from localhost
   ```

5. **Use HTTPS in Production**
   - JWT tokens should ONLY be transmitted over HTTPS
   - Never send tokens over HTTP in production

6. **Token Storage (Frontend)**
   - **Best**: HttpOnly cookies (prevents XSS)
   - **Good**: Secure localStorage with XSS protection
   - **Avoid**: Regular cookies or sessionStorage

7. **Implement Token Revocation** (Future Enhancement)
   - Store active tokens in Redis
   - Allow users to logout (invalidate token)
   - Implement token blacklist

---

## Token Structure

### Access Token Payload

```json
{
  "sub": "user-uuid",           // User ID
  "company_id": "company-uuid",  // Company ID (multi-tenant)
  "exp": 1700000000,            // Expiration timestamp
  "iat": 1699913600,            // Issued at timestamp
  "type": "access"              // Token type
}
```

### Refresh Token Payload

```json
{
  "sub": "user-uuid",
  "company_id": "company-uuid",
  "exp": 1702505600,            // 30 days later
  "iat": 1699913600,
  "type": "refresh"
}
```

---

## Troubleshooting

### Error: "Could not validate credentials"

**Cause**: Invalid or expired token

**Solution**:
1. Check token is in correct format: `Bearer <token>`
2. Verify token hasn't expired (1 day)
3. Use refresh token to get new access token

### Error: "Inactive user"

**Cause**: User account is deactivated

**Solution**: Activate user in database or contact admin

### Error: "Not enough permissions"

**Cause**: Trying to access superuser endpoint without superuser role

**Solution**: Use superuser account or contact admin

---

## Next Steps

1. ✅ Run migrations to ensure database is up to date
2. ✅ Create your first company using `/auth/setup`
3. ✅ Login and test token generation
4. 🔨 Protect your endpoints by adding `Depends(get_current_active_user)`
5. 🔨 Implement role-based permissions
6. 🔨 Add logout functionality (token revocation)
7. 🔨 Implement password reset flow

---

**Documentation complete!** 🎉

For questions or issues, check the code in:
- `app/core/jwt.py` - JWT utilities
- `app/core/auth.py` - Authentication dependencies
- `app/api/v1/auth.py` - Auth endpoints
