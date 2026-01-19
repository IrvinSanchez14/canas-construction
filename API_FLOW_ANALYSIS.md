# API Flow Analysis - Canas Construction

## Overview
This document analyzes the current API implementation against the required business flow and identifies gaps and recommendations.

## Required Business Flow

1. **User creates a client** ✅
2. **Clients can have many projects** ✅
3. **Each project has a visit** ✅
   - In this visit, user can add information about the project
   - User can add photos or videos (max 10)
4. **Each visit has a budget** ❌
   - User creates a list of products/items to create the project
   - Budget structure matches the PDF example (work details with line items)
5. **When budget is accepted by client, project status changes to "accepted"** ❌

---

## Current Implementation Status

### ✅ IMPLEMENTED

#### 1. Client Model (`app/models/client.py`)
- **Status**: ✅ Fully implemented
- **Features**:
  - Client creation with name, email, phone
  - Multi-tenant support (company_id)
  - Relationship to projects (one-to-many)
- **API Endpoints**: `/api/v1/clients` (CRUD operations)

#### 2. Project Model (`app/models/project.py`)
- **Status**: ✅ Fully implemented
- **Features**:
  - Project creation with client relationship
  - Project status enum (LEAD, QUOTED, APPROVED, IN_PROGRESS, COMPLETED, CANCELLED, ON_HOLD)
  - Multiple projects per client (one-to-many)
  - Relationship to visits (one-to-many)
- **API Endpoints**: `/api/v1/projects` (CRUD operations)
- **Note**: Project status has `APPROVED` but **NOT** `ACCEPTED`

#### 3. Visit Model (`app/models/visit.py`)
- **Status**: ✅ Partially implemented
- **Features**:
  - Visit creation with project relationship
  - Visit status workflow (PLANNING, IN_REVIEW, APPROVED, INSPECTION_REQUIRED, VISITED)
  - Images and attachments storage (JSON array)
  - Visit items storage (JSON array) - items collected during visit
  - Inspection notes and financial estimates
- **API Endpoints**: `/api/v1/visits` (CRUD operations)
- **Gaps**:
  - ❌ **NO validation for max 10 photos/videos**
  - ❌ **Images and attachments stored as JSON, not separate entities**

---

### ❌ MISSING / INCOMPLETE

#### 1. Budget Model
- **Status**: ❌ **NOT IMPLEMENTED**
- **Current State**:
  - Visit model has `visit_items` (JSON) which stores items collected during visit
  - This is NOT a separate Budget entity
  - No budget acceptance workflow
  - No relationship between budget and visit
  
- **What's Needed**:
  - Separate `Budget` model/table
  - Budget should have:
    - Relationship to Visit (one-to-one or one-to-many)
    - Budget status (DRAFT, PENDING_APPROVAL, ACCEPTED, REJECTED)
    - Budget items (line items matching PDF structure)
    - Total amount calculation
    - Acceptance date and accepted_by (client/user)
  
- **PDF Structure Analysis**:
  Based on the PDF example, a budget should have:
  - **Sections** (e.g., "PROVISIONALS", "DEMO", "ELECTRICAL", "FLOORING and TILE", etc.)
  - **Line Items** within each section:
    - Description
    - Unit (each, sq ft, ft, etc.)
    - Quantity
    - Unit price
    - Subtotal
  - **Total** amount

#### 2. Budget Acceptance Workflow
- **Status**: ❌ **NOT IMPLEMENTED**
- **What's Needed**:
  - When budget status changes to `ACCEPTED`:
    - Project status should automatically change to `ACCEPTED` (or use existing `APPROVED`)
    - Track who accepted (client or user)
    - Track acceptance date
    - Possibly trigger notifications/events

#### 3. Visit Media Validation
- **Status**: ❌ **NOT IMPLEMENTED**
- **What's Needed**:
  - Validation in Visit schema/service to limit:
    - Maximum 10 photos
    - Maximum 10 videos
    - Or maximum 10 total media files (photos + videos)
  - File type validation (images: jpg, png, etc.; videos: mp4, mov, etc.)
  - File size validation

#### 4. Project Status - "ACCEPTED"
- **Status**: ⚠️ **PARTIALLY IMPLEMENTED**
- **Current State**:
  - ProjectStatus enum has: LEAD, QUOTED, APPROVED, IN_PROGRESS, COMPLETED, CANCELLED, ON_HOLD
  - No `ACCEPTED` status
- **Recommendation**:
  - Either add `ACCEPTED` status OR use existing `APPROVED` status
  - Need to clarify business logic: Is "accepted" different from "approved"?

---

## Recommendations

### 1. Create Budget Model

**RECOMMENDATION: Hybrid Approach (Catalog Items + Custom Items)**

Based on the PDF analysis, I recommend a **HYBRID approach** that leverages the existing `CatalogItem` system:

**Why Hybrid?**
- ✅ **Reusable Products**: Items like "Faucet Vibrant brushed Nickel", "Panasonic Exaust fan/heater" are standard products that should be in catalog
- ✅ **Price Flexibility**: Prices change over time, so budget items should store the actual price used (not just reference catalog)
- ✅ **Custom Items**: Some items are project-specific (e.g., "Demo tile in wall" - 64 sq ft) and shouldn't be in catalog
- ✅ **Historical Tracking**: Catalog stores base price, budget item stores actual price used at time of quote
- ✅ **Faster Budget Creation**: Users can quickly add items from catalog, then customize quantities/prices

**Suggested Structure:**
```python
class BudgetStatus(enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVISED = "revised"

class Budget(BaseModel):
    __tablename__ = "budgets"
    
    # Basic info
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(BudgetStatus), default=BudgetStatus.DRAFT)
    
    # Financial (calculated from items)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    
    # Relationships
    visit_id = Column(UUID, ForeignKey("visits.id"), nullable=False, unique=True)
    accepted_by_user_id = Column(UUID, ForeignKey("users.id"), nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    
    # Relationships
    visit = relationship("Visit", back_populates="budget")
    budget_items = relationship("BudgetItem", back_populates="budget", cascade="all, delete-orphan")

class BudgetItem(BaseModel):
    __tablename__ = "budget_items"
    
    # Line item details
    section_name = Column(String(255), nullable=True)  # e.g., "PROVISIONALS", "DEMO", "ELECTRICAL"
    description = Column(Text, nullable=False)
    unit = Column(String(50), nullable=True)  # "each", "sq ft", "ft", "hr", etc.
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)  # Actual price used (may differ from catalog)
    subtotal = Column(Numeric(12, 2), nullable=False)  # quantity * unit_price
    
    # Ordering
    order_index = Column(Integer, nullable=False)  # For ordering items within section
    
    # OPTIONAL: Reference to catalog item (if item came from catalog)
    catalog_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalog_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Reference to catalog item if this was added from catalog"
    )
    
    # Relationships
    budget_id = Column(UUID, ForeignKey("budgets.id"), nullable=False)
    budget = relationship("Budget", back_populates="budget_items")
    catalog_item = relationship("CatalogItem", foreign_keys=[catalog_item_id])
```

**Workflow:**
1. **User creates budget items** by either:
   - **Selecting from catalog**: Choose catalog item → auto-fill name, unit, base price → user can modify price/quantity
   - **Adding custom item**: Enter description, unit, quantity, price manually
2. **Budget items store actual prices** used (even if from catalog, price can be customized)
3. **Total is calculated** from all budget items
4. **When budget accepted**, project status changes to APPROVED/ACCEPTED

**Benefits:**
- ✅ Fast budget creation using catalog
- ✅ Price flexibility per project
- ✅ Support for one-off custom items
- ✅ Historical price tracking (catalog price vs. actual price used)
- ✅ Easy to see which items came from catalog vs. custom

**PDF Examples Analysis:**

From the PDF, items fall into these categories:

1. **Catalog Items (Reusable Products)** - Should be in catalog:
   - "Faucet Vibrant brushed Nickel" - $236.58
   - "Tub spout Vibrant brushed nickel" - $61.06
   - "Panasonic Exaust fan/heater and ligth" - $464.25
   - "toilet 1.28 Gpf white" - $326.96
   - These are standard products used across multiple projects

2. **Catalog Items (Reusable Services)** - Could be in catalog:
   - "Remove and disposal Toilet" - $125.00 (each)
   - "Remove and Disposal Tub" - $250.00 (each)
   - "Install new Vanity Ligth" - $300.00 (each)
   - Standard services with standard pricing

3. **Custom Items (Project-Specific)** - Should NOT be in catalog:
   - "Demo tile in wall" - 64 sq ft at $2.00/sq ft = $128.00
   - "Cover and protect walls and flooring" - 75 sq ft at $1.50/sq ft = $112.50
   - "Install new tile in tub walls" - 88 sq ft at $35.00/sq ft = $3,080.00
   - These are project-specific measurements and quantities

**Recommendation:**
- **Create catalog items** for standard products/services (items #1 and #2 above)
- **Allow custom items** in budgets for project-specific work (item #3 above)
- **Budget items can reference catalog** but store actual price used (prices change over time)
- **User workflow**: Select from catalog → customize if needed → add custom items as needed

### 2. Add Budget Acceptance Logic

**In Budget Service:**
```python
def accept_budget(
    self,
    budget_id: UUID,
    company_id: UUID,
    accepted_by_user_id: UUID
) -> tuple[Budget, Project]:
    """
    Accept a budget and update project status.
    
    Returns:
        (updated_budget, updated_project)
    """
    budget = self.get_budget(budget_id, company_id)
    
    # Update budget
    budget.status = BudgetStatus.ACCEPTED
    budget.accepted_by_user_id = accepted_by_user_id
    budget.accepted_at = datetime.utcnow()
    
    # Update project status
    project = budget.visit.project
    project.status = ProjectStatus.APPROVED  # or ProjectStatus.ACCEPTED if added
    
    self.budget_repository.db.flush()
    return budget, project
```

### 3. Add Visit Media Validation

**In Visit Schema:**
```python
from pydantic import field_validator

class VisitBase(BaseModel):
    # ... existing fields ...
    
    images: Optional[List[str]] = None
    attachments: Optional[List[str]] = None
    
    @field_validator('images')
    @classmethod
    def validate_images(cls, v):
        if v and len(v) > 10:
            raise ValueError("Maximum 10 images allowed per visit")
        return v
    
    @field_validator('attachments')
    @classmethod
    def validate_attachments(cls, v):
        if v and len(v) > 10:
            raise ValueError("Maximum 10 attachments allowed per visit")
        # Or combine: if (images or []) + (attachments or []) > 10
        return v
```

**In Visit Service:**
```python
def create_visit(self, ...):
    # ... existing validation ...
    
    # Validate media limits
    total_media = (visit_data.images or []) + (visit_data.attachments or [])
    if len(total_media) > 10:
        raise ValidationException("Maximum 10 photos/videos allowed per visit")
    
    # ... rest of creation logic ...
```

### 4. Update Project Status Enum (if needed)

**Option A: Add ACCEPTED status**
```python
class ProjectStatus(enum.Enum):
    LEAD = "lead"
    QUOTED = "quoted"
    APPROVED = "approved"
    ACCEPTED = "accepted"  # NEW
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"
```

**Option B: Use existing APPROVED status**
- When budget is accepted, set project status to `APPROVED`
- This might be semantically correct if "approved" means "client approved the budget"

---

## Database Migration Requirements

1. **Create budgets table**
   - Add foreign key to visits
   - Add status enum
   - Add acceptance tracking fields

2. **Create budget_items table**
   - Add foreign key to budgets
   - Add section_name, description, unit, quantity, unit_price, subtotal
   - Add order_index for sorting

3. **Update visits table** (if needed)
   - Add relationship to budget (one-to-one)

4. **Update projects table** (if adding ACCEPTED status)
   - Update ProjectStatus enum in database

---

## API Endpoints Needed

### Budget Endpoints
- `POST /api/v1/budgets` - Create budget for a visit
- `GET /api/v1/budgets/{budget_id}` - Get budget details with items
- `GET /api/v1/visits/{visit_id}/budget` - Get budget for a visit
- `PUT /api/v1/budgets/{budget_id}` - Update budget
- `POST /api/v1/budgets/{budget_id}/items` - Add budget item (from catalog or custom)
- `POST /api/v1/budgets/{budget_id}/items/from-catalog` - Add budget item from catalog (with optional price override)
- `PUT /api/v1/budgets/{budget_id}/items/{item_id}` - Update budget item
- `DELETE /api/v1/budgets/{budget_id}/items/{item_id}` - Delete budget item
- `POST /api/v1/budgets/{budget_id}/accept` - Accept budget (triggers project status change)
- `POST /api/v1/budgets/{budget_id}/reject` - Reject budget
- `GET /api/v1/budgets/{budget_id}/recalculate` - Recalculate total from items

### Catalog Integration (Already Exists ✅)
- `GET /api/v1/catalog_items` - List catalog items (for budget creation UI)
- `GET /api/v1/catalog_items/by-unity/{unity}` - Get items by unit type
- These endpoints can be used by frontend to populate dropdowns when creating budget items

---

## Summary

### ✅ What Works
- Client creation and management
- Project creation with client relationship
- Visit creation with project relationship
- Basic visit data storage (images, attachments, items)

### ❌ What's Missing
1. **Separate Budget entity** - Currently only `visit_items` JSON field
2. **Budget acceptance workflow** - No logic to accept/reject budgets
3. **Project status update on budget acceptance** - No automatic status change
4. **Media validation** - No max 10 photos/videos limit enforced
5. **Budget items structure** - No proper line items matching PDF structure

### 💡 Key Recommendation: Hybrid Budget Model
**Use existing CatalogItem system + Custom Budget Items:**
- ✅ Catalog items for reusable products/services (e.g., "Faucet Vibrant brushed Nickel")
- ✅ Custom budget items for project-specific work (e.g., "Demo tile in wall" - 64 sq ft)
- ✅ Budget items can reference catalog but store actual price used (prices change over time)
- ✅ Best of both worlds: Fast budget creation + Flexibility for custom items

### 🔧 Recommendations Priority
1. **HIGH**: Create Budget model and BudgetItem model
2. **HIGH**: Add budget acceptance endpoint and logic
3. **MEDIUM**: Add visit media validation (max 10)
4. **MEDIUM**: Decide on ProjectStatus.ACCEPTED vs using APPROVED
5. **LOW**: Add file type validation for media uploads

---

## Frontend (crm-frontend) Status

### ✅ Implemented Features
- **Auth**: Login/logout functionality
- **Clients**: Client management (list, create)
- **Projects**: Project management (list, create, detail view)
- **Project Categories**: Category management
- **Dashboard**: Main dashboard page

### ❌ Missing Features
- **Visits**: No visit management UI
- **Budgets**: No budget management UI
- **Media Upload**: No file upload components for visit photos/videos

### Frontend Architecture
- Well-structured with feature-based architecture
- Uses React 19, TypeScript, Vite
- Follows SOLID principles
- Has API client setup (`api.client.ts`)
- Ready to add new features following existing patterns

---

## Next Steps

1. Review and approve this analysis
2. Decide on ProjectStatus.ACCEPTED vs APPROVED
3. Create Budget and BudgetItem models
4. Create database migrations
5. Implement Budget service and API endpoints
6. Add budget acceptance workflow
7. Add visit media validation
8. **Frontend**: Create visits feature module
9. **Frontend**: Create budgets feature module
10. **Frontend**: Add media upload components

---

## Questions for Clarification

1. **Budget-Visit Relationship**: Should it be one-to-one (one budget per visit) or one-to-many (multiple budget versions per visit)?
2. **Project Status**: Should we add `ACCEPTED` status or use existing `APPROVED`?
3. **Media Limit**: Is it 10 photos + 10 videos, or 10 total media files?
4. **Budget Sections**: Should sections be stored as separate entities or just as a field in BudgetItem?
5. **Budget Versioning**: Should we track budget revisions/history?
