# API Documentation - Multi-Tenant Endpoints

## Base URL
```
http://localhost:8000/api/v1
```

## Companies Endpoints

### 1. Create Company
**POST** `/companies/`

Create a new company in the system.

**Request Body:**
```json
{
  "name": "Canas Construction",
  "email": "info@canas.com",
  "phone": "555-1234",
  "address": "123 Main Street, City, State"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "name": "Canas Construction",
  "email": "info@canas.com",
  "phone": "555-1234",
  "address": "123 Main Street, City, State",
  "is_active": true,
  "created_at": "2024-11-28T12:00:00",
  "updated_at": "2024-11-28T12:00:00"
}
```

### 2. List Companies
**GET** `/companies/`

Get all companies with pagination.

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100, max: 1000)
- `is_active`: Filter by active status (optional)

**Example:**
```
GET /companies/?skip=0&limit=10&is_active=true
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "Canas Construction",
    "email": "info@canas.com",
    "phone": "555-1234",
    "address": "123 Main Street",
    "is_active": true,
    "created_at": "2024-11-28T12:00:00",
    "updated_at": "2024-11-28T12:00:00"
  }
]
```

### 3. Get Company
**GET** `/companies/{company_id}`

Get a specific company by ID.

**Response:** `200 OK`

### 4. Update Company
**PUT** `/companies/{company_id}`

Update a company. All fields are optional.

**Request Body:**
```json
{
  "name": "Updated Company Name",
  "is_active": false
}
```

**Response:** `200 OK`

### 5. Delete Company
**DELETE** `/companies/{company_id}`

Delete a company (cascade deletes all users and roles).

**Response:** `204 No Content`

---

## Roles Endpoints

### 1. Create Role
**POST** `/roles/`

Create a new role for a company.

**Request Body:**
```json
{
  "name": "Administrator",
  "description": "Full access to all features",
  "company_id": 1
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "name": "Administrator",
  "description": "Full access to all features",
  "company_id": 1,
  "is_active": true,
  "created_at": "2024-11-28T12:00:00",
  "updated_at": "2024-11-28T12:00:00"
}
```

**Business Rules:**
- Role name must be unique within the company
- Company must exist

### 2. List Roles
**GET** `/roles/`

Get all roles with optional filters.

**Query Parameters:**
- `company_id`: Filter by company (recommended for multi-tenant)
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100, max: 1000)
- `is_active`: Filter by active status (optional)

**Example:**
```
GET /roles/?company_id=1&is_active=true
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "Administrator",
    "description": "Full access",
    "company_id": 1,
    "is_active": true,
    "created_at": "2024-11-28T12:00:00",
    "updated_at": "2024-11-28T12:00:00"
  },
  {
    "id": 2,
    "name": "Manager",
    "description": "Project management access",
    "company_id": 1,
    "is_active": true,
    "created_at": "2024-11-28T12:00:00",
    "updated_at": "2024-11-28T12:00:00"
  }
]
```

### 3. Get Role
**GET** `/roles/{role_id}?company_id={company_id}`

Get a specific role by ID.

**Query Parameters:**
- `company_id`: Optional company filter for data isolation

**Response:** `200 OK`

### 4. Update Role
**PUT** `/roles/{role_id}?company_id={company_id}`

Update a role.

**Request Body:**
```json
{
  "name": "Super Administrator",
  "is_active": true
}
```

**Response:** `200 OK`

### 5. Delete Role
**DELETE** `/roles/{role_id}?company_id={company_id}`

Delete a role.

**Response:** `204 No Content`

---

## Users Endpoints

### 1. Create User
**POST** `/users/`

Create a new user for a company.

**Request Body:**
```json
{
  "email": "john.doe@canas.com",
  "username": "johndoe",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "555-5678",
  "company_id": 1,
  "role_ids": [1, 2]
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "email": "john.doe@canas.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "555-5678",
  "company_id": 1,
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-11-28T12:00:00",
  "updated_at": "2024-11-28T12:00:00",
  "roles": [
    {
      "id": 1,
      "name": "Administrator",
      "description": "Full access",
      "company_id": 1,
      "is_active": true,
      "created_at": "2024-11-28T12:00:00",
      "updated_at": "2024-11-28T12:00:00"
    }
  ]
}
```

**Business Rules:**
- Email must be unique across all companies
- All roles must belong to the same company as the user
- Password is automatically hashed before storage
- Company must exist

### 2. List Users
**GET** `/users/`

Get all users with optional filters.

**Query Parameters:**
- `company_id`: Filter by company (HIGHLY recommended for multi-tenant)
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100, max: 1000)
- `is_active`: Filter by active status (optional)

**Example:**
```
GET /users/?company_id=1&is_active=true&limit=50
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "email": "john.doe@canas.com",
    "username": "johndoe",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "555-5678",
    "company_id": 1,
    "is_active": true,
    "is_superuser": false,
    "created_at": "2024-11-28T12:00:00",
    "updated_at": "2024-11-28T12:00:00",
    "roles": [...]
  }
]
```

### 3. Get User
**GET** `/users/{user_id}?company_id={company_id}`

Get a specific user by ID.

**Query Parameters:**
- `company_id`: Optional company filter for data isolation

**Response:** `200 OK`

### 4. Update User
**PUT** `/users/{user_id}?company_id={company_id}`

Update a user.

**Request Body:**
```json
{
  "first_name": "Jonathan",
  "phone": "555-9999",
  "is_active": false,
  "role_ids": [1, 2, 3]
}
```

**Notes:**
- All fields are optional
- `password` field will be hashed before storing
- `role_ids` will replace ALL current roles

**Response:** `200 OK`

### 5. Delete User
**DELETE** `/users/{user_id}?company_id={company_id}`

Delete a user.

**Response:** `204 No Content`

### 6. Login
**POST** `/users/login`

Authenticate a user with email and password.

**Request Body:**
```json
{
  "email": "john.doe@canas.com",
  "password": "SecurePassword123!"
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "john.doe@canas.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "company_id": 1,
  "is_active": true,
  "is_superuser": false,
  "roles": [...]
}
```

**Error Response:** `401 Unauthorized`
```json
{
  "detail": "Invalid email or password"
}
```

**Note:** In production, this should return a JWT token instead of the user object.

---

## Common Response Codes

- `200 OK` - Successful GET/PUT request
- `201 Created` - Successful POST request
- `204 No Content` - Successful DELETE request
- `400 Bad Request` - Invalid input or business rule violation
- `401 Unauthorized` - Authentication failed
- `404 Not Found` - Resource not found
- `422 Validation Error` - Pydantic validation failed

---

## Example Workflow: Creating a Complete Company Setup

### Step 1: Create Company
```bash
curl -X POST http://localhost:8000/api/v1/companies/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Canas Construction",
    "email": "info@canas.com",
    "phone": "555-1234",
    "address": "123 Main St"
  }'
```

Response: `company_id = 1`

### Step 2: Create Roles for the Company
```bash
# Create Administrator role
curl -X POST http://localhost:8000/api/v1/roles/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Administrator",
    "description": "Full system access",
    "company_id": 1
  }'

# Create Manager role
curl -X POST http://localhost:8000/api/v1/roles/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Manager",
    "description": "Project management",
    "company_id": 1
  }'

# Create Worker role
curl -X POST http://localhost:8000/api/v1/roles/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Worker",
    "description": "Field worker",
    "company_id": 1
  }'
```

Response: `role_id = 1, 2, 3`

### Step 3: Create Users with Roles
```bash
# Create admin user
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@canas.com",
    "username": "admin",
    "password": "AdminPass123!",
    "first_name": "Admin",
    "last_name": "User",
    "company_id": 1,
    "role_ids": [1]
  }'

# Create manager user
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "manager@canas.com",
    "username": "manager",
    "password": "ManagerPass123!",
    "first_name": "John",
    "last_name": "Manager",
    "company_id": 1,
    "role_ids": [2]
  }'
```

### Step 4: Login
```bash
curl -X POST http://localhost:8000/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@canas.com",
    "password": "AdminPass123!"
  }'
```

---

## Testing with Swagger UI

Once the server is running, visit:
```
http://localhost:8000/docs
```

You'll see interactive API documentation where you can test all endpoints.

---

## Data Isolation Best Practices

1. **Always filter by company_id** when querying users or roles
2. **Validate ownership** before updates or deletes
3. **Use query parameters** to enforce company isolation
4. In production, implement middleware to automatically inject company_id from authenticated user

Example:
```python
# BAD - Returns all users from all companies
GET /users/

# GOOD - Returns only users from company 1
GET /users/?company_id=1
```
