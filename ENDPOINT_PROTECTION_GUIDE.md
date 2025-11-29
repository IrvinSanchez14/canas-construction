# 🔒 Endpoint Protection Guide

## ✅ What's Already Protected

### **User Endpoints** - FULLY PROTECTED ✅
All `/api/v1/users/*` endpoints now require authentication:
- ✅ `POST /users/` - Create user (auth required, enforces own company)
- ✅ `GET /users/` - List users (auth required, auto-filtered to own company)
- ✅ `GET /users/{id}` - Get user (auth required, own company only)
- ✅ `PUT /users/{id}` - Update user (auth required, own company only)
- ✅ `DELETE /users/{id}` - Delete user (auth required, own company only)

## ❌ What Still Needs Protection

These endpoints are **NOT yet protected** and need authentication added:
- ❌ `/api/v1/companies/*`
- ❌ `/api/v1/roles/*`
- ❌ `/api/v1/clients/*`
- ❌ `/api/v1/projects/*`
- ❌ `/api/v1/project-categories/*`
- ❌ `/api/v1/catalog-items/*`

---

## 🔐 How to Protect an Endpoint

### Step-by-Step Example: Protecting Clients Endpoint

#### **Before (Unprotected):**
```python
@router.get("/", response_model=List[ClientResponse])
def list_clients(
    company_id: UUID = Query(..., description="Filter by company ID (REQUIRED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: ClientService = Depends(get_client_service)
):
    """Get all clients for a company."""
    return service.get_clients(company_id, skip, limit)
```

#### **After (Protected):**
```python
from app.core.auth import get_current_active_user  # 1. Import auth dependency
from app.models import User
from fastapi import HTTPException

@router.get("/", response_model=List[ClientResponse])
def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),  # 2. Add auth parameter
    service: ClientService = Depends(get_client_service)
):
    """
    Get all clients for your company.

    🔒 **Authentication Required**

    **Authorization:**
    - Automatically shows only clients from your company
    - Multi-tenant isolation enforced
    """
    # 3. Use current_user.company_id instead of parameter
    return service.get_clients(
        company_id=current_user.company_id,  # Enforced!
        skip=skip,
        limit=limit
    )
```

### What Changed?

1. **Added import:** `from app.core.auth import get_current_active_user`
2. **Removed `company_id` parameter** - no longer from query params
3. **Added `current_user` parameter** with dependency injection
4. **Auto-set company_id** from authenticated user's company

---

## 📝 Complete Example: Protecting All Client Endpoints

Here's the complete `app/api/v1/clients.py` with all endpoints protected:

```python
"""
Client endpoints - ALL PROTECTED 🔒
"""

from fastapi import APIRouter, Depends, status, Query, HTTPException
from typing import List
from uuid import UUID

from app.core.dependencies import get_client_service
from app.core.auth import get_current_active_user  # Import auth
from app.models import User
from app.services import ClientService
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client: ClientCreate,
    current_user: User = Depends(get_current_active_user),  # 🔒 Auth required
    service: ClientService = Depends(get_client_service)
):
    """
    Create a new client.

    🔒 Authentication Required

    Authorization:
    - Can only create clients for your own company
    """
    # Enforce multi-tenant: client must belong to user's company
    if client.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create clients for your own company"
        )

    return service.create_client(client)


@router.get("/", response_model=List[ClientResponse])
def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),  # 🔒 Auth required
    service: ClientService = Depends(get_client_service)
):
    """
    List all clients for your company.

    🔒 Authentication Required

    Authorization:
    - Automatically filtered to your company only
    """
    return service.get_clients(
        company_id=current_user.company_id,  # Auto-filtered!
        skip=skip,
        limit=limit
    )


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: UUID,
    current_user: User = Depends(get_current_active_user),  # 🔒 Auth required
    service: ClientService = Depends(get_client_service)
):
    """
    Get a specific client.

    🔒 Authentication Required

    Authorization:
    - Can only view clients from your own company
    """
    return service.get_client(client_id, company_id=current_user.company_id)


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: UUID,
    client: ClientUpdate,
    current_user: User = Depends(get_current_active_user),  # 🔒 Auth required
    service: ClientService = Depends(get_client_service)
):
    """
    Update a client.

    🔒 Authentication Required

    Authorization:
    - Can only update clients from your own company
    """
    return service.update_client(client_id, client, company_id=current_user.company_id)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: UUID,
    current_user: User = Depends(get_current_active_user),  # 🔒 Auth required
    service: ClientService = Depends(get_client_service)
):
    """
    Delete a client.

    🔒 Authentication Required

    Authorization:
    - Can only delete clients from your own company
    """
    service.delete_client(client_id, company_id=current_user.company_id)
    return None
```

---

## 🎯 Quick Checklist for Each Endpoint

For EVERY endpoint you want to protect:

- [ ] **Import auth dependency:**
  ```python
  from app.core.auth import get_current_active_user
  from app.models import User
  ```

- [ ] **Add auth parameter:**
  ```python
  current_user: User = Depends(get_current_active_user)
  ```

- [ ] **Remove `company_id` from query parameters** (if present)

- [ ] **Use `current_user.company_id`** instead of parameter

- [ ] **Add validation** for create/update operations:
  ```python
  if data.company_id != current_user.company_id:
      raise HTTPException(403, "Access denied")
  ```

- [ ] **Update docstring** to indicate 🔒 Authentication Required

---

## 🔐 Different Auth Levels

### 1. Active User (Most Common)
```python
current_user: User = Depends(get_current_active_user)
```
✅ Use for: All normal endpoints

### 2. Any User (Including Inactive)
```python
current_user: User = Depends(get_current_user)
```
⚠️ Use for: Special cases where inactive users need access

### 3. Superuser Only
```python
current_user: User = Depends(get_current_superuser)
```
🔒 Use for: Admin-only operations (delete company, system settings, etc.)

---

## 📊 Multi-Tenant Isolation Patterns

### Pattern 1: Auto-Filter by Company
```python
# User sees only their company's data
def list_items(current_user: User = Depends(get_current_active_user)):
    return service.get_items(company_id=current_user.company_id)
```

### Pattern 2: Validate Company Ownership
```python
# User creates resource in their company only
def create_item(item: ItemCreate, current_user: User = Depends(...)):
    if item.company_id != current_user.company_id:
        raise HTTPException(403, "Access denied")
    return service.create_item(item)
```

### Pattern 3: Validate on Read
```python
# User retrieves specific resource from their company
def get_item(item_id: UUID, current_user: User = Depends(...)):
    item = service.get_item(item_id, company_id=current_user.company_id)
    # Service will raise 404 if not found or wrong company
    return item
```

---

## ⚡ Testing Protected Endpoints

### 1. Get Access Token
```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"password"}' \
  | jq -r '.access_token')
```

### 2. Use Token in Request
```bash
curl -X GET "http://localhost:8000/api/v1/clients/" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Try Without Token (Should Fail)
```bash
curl -X GET "http://localhost:8000/api/v1/clients/"
# Should return 401 Unauthorized
```

---

## 🚨 Common Mistakes to Avoid

### ❌ Mistake 1: Trusting User Input for Company ID
```python
# BAD - User can pass any company_id
def list_items(company_id: UUID = Query(...)):
    return service.get_items(company_id)
```

### ✅ Fix: Use Authenticated User's Company
```python
# GOOD - Company ID from token
def list_items(current_user: User = Depends(get_current_active_user)):
    return service.get_items(company_id=current_user.company_id)
```

### ❌ Mistake 2: Forgetting to Validate Create/Update
```python
# BAD - User could create items for other companies
def create_item(item: ItemCreate, current_user: User = Depends(...)):
    return service.create_item(item)  # No validation!
```

### ✅ Fix: Validate Company Ownership
```python
# GOOD - Validate company matches
def create_item(item: ItemCreate, current_user: User = Depends(...)):
    if item.company_id != current_user.company_id:
        raise HTTPException(403, "Access denied")
    return service.create_item(item)
```

---

## 📝 Next Steps

1. ✅ User endpoints are protected
2. 🔨 Protect client endpoints (use example above)
3. 🔨 Protect project endpoints
4. 🔨 Protect project-category endpoints
5. 🔨 Protect catalog-item endpoints
6. 🔨 Protect role endpoints
7. 🔨 Protect company endpoints (consider superuser-only)

**Copy the pattern from users.py to all other endpoint files!**

---

## 💡 Pro Tips

1. **Start Server:** `uvicorn app.main:app --reload`
2. **Test in Browser:** Go to `http://localhost:8000/docs`
3. **Click "Authorize"** button in Swagger UI
4. **Enter token:** `Bearer YOUR_TOKEN_HERE`
5. **Test protected endpoints** - should work!
6. **Clear token** - endpoints should return 401

---

**Your user endpoints are fully protected!** 🎉
Now apply the same pattern to protect all other endpoints.
