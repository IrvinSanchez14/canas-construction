"""
Tests for Budget Schemas - validation of categories, items, and versioning.

Tests Pydantic validation rules including:
- Category image limit (max 3)
- Item subtotal auto-calculation
- Budget creation with nested categories and items
"""

import pytest
from decimal import Decimal
from uuid import uuid4
from pydantic import ValidationError

from app.schemas.budget import (
    BudgetItemCreate,
    BudgetItemUpdate,
    BudgetCategoryCreate,
    BudgetCreate,
    BudgetUpdate,
)
from app.schemas.budget_category import BudgetCategoryUpdate
from app.schemas.budget_version import BudgetVersionResponse, BudgetVersionListResponse
from app.models.budget import BudgetStatus


# --- BudgetItemCreate Tests ---

class TestBudgetItemCreate:
    def test_create_item_valid(self):
        """Test creating a valid budget item."""
        item = BudgetItemCreate(
            description="Install drywall",
            unit="sq ft",
            quantity=Decimal("100.00"),
            unit_price=Decimal("5.50"),
        )
        assert item.description == "Install drywall"
        assert item.unit == "sq ft"
        assert item.quantity == Decimal("100.00")
        assert item.unit_price == Decimal("5.50")
        assert item.subtotal == Decimal("550.00")  # Auto-calculated

    def test_item_auto_calculate_subtotal(self):
        """Test that subtotal is auto-calculated from quantity * unit_price."""
        item = BudgetItemCreate(
            description="Paint walls",
            quantity=Decimal("200.00"),
            unit_price=Decimal("3.25"),
        )
        assert item.subtotal == Decimal("650.00")

    def test_item_explicit_subtotal(self):
        """Test providing explicit subtotal overrides calculation."""
        item = BudgetItemCreate(
            description="Custom item",
            quantity=Decimal("10.00"),
            unit_price=Decimal("5.00"),
            subtotal=Decimal("45.00"),  # Discounted
        )
        assert item.subtotal == Decimal("45.00")

    def test_item_with_catalog_reference(self):
        """Test item with catalog_item_id."""
        catalog_id = uuid4()
        item = BudgetItemCreate(
            description="Catalog item",
            quantity=Decimal("5.00"),
            unit_price=Decimal("20.00"),
            catalog_item_id=catalog_id,
        )
        assert item.catalog_item_id == catalog_id

    def test_item_quantity_must_be_positive(self):
        """Test that quantity must be > 0."""
        with pytest.raises(ValidationError):
            BudgetItemCreate(
                description="Bad item",
                quantity=Decimal("0"),
                unit_price=Decimal("10.00"),
            )

    def test_item_unit_price_can_be_zero(self):
        """Test that unit_price can be 0 (free items)."""
        item = BudgetItemCreate(
            description="Free item",
            quantity=Decimal("1.00"),
            unit_price=Decimal("0"),
        )
        assert item.unit_price == Decimal("0")
        assert item.subtotal == Decimal("0")

    def test_item_negative_unit_price_rejected(self):
        """Test that negative unit_price is rejected."""
        with pytest.raises(ValidationError):
            BudgetItemCreate(
                description="Bad price",
                quantity=Decimal("1.00"),
                unit_price=Decimal("-5.00"),
            )


# --- BudgetItemUpdate Tests ---

class TestBudgetItemUpdate:
    def test_partial_update(self):
        """Test partial update with only some fields."""
        update = BudgetItemUpdate(description="Updated description")
        data = update.model_dump(exclude_unset=True)
        assert data == {"description": "Updated description"}

    def test_update_quantity_and_price(self):
        """Test updating quantity and price."""
        update = BudgetItemUpdate(
            quantity=Decimal("20.00"),
            unit_price=Decimal("15.00"),
        )
        assert update.quantity == Decimal("20.00")
        assert update.unit_price == Decimal("15.00")

    def test_empty_update(self):
        """Test empty update (no fields set)."""
        update = BudgetItemUpdate()
        data = update.model_dump(exclude_unset=True)
        assert data == {}


# --- BudgetCategoryCreate Tests ---

class TestBudgetCategoryCreate:
    def test_create_category_valid(self):
        """Test creating a valid category."""
        category = BudgetCategoryCreate(
            name="Electrical",
            description="All electrical work",
            order_index=1,
        )
        assert category.name == "Electrical"
        assert category.description == "All electrical work"
        assert category.items == []

    def test_category_with_items(self):
        """Test creating a category with items."""
        category = BudgetCategoryCreate(
            name="Demolition",
            items=[
                BudgetItemCreate(
                    description="Remove drywall",
                    quantity=Decimal("100.00"),
                    unit_price=Decimal("3.00"),
                ),
                BudgetItemCreate(
                    description="Haul debris",
                    unit="load",
                    quantity=Decimal("2.00"),
                    unit_price=Decimal("250.00"),
                ),
            ]
        )
        assert len(category.items) == 2
        assert category.items[0].subtotal == Decimal("300.00")
        assert category.items[1].subtotal == Decimal("500.00")

    def test_category_with_3_images(self):
        """Test category with exactly 3 images (max allowed)."""
        category = BudgetCategoryCreate(
            name="Plumbing",
            images=[
                "https://cdn.example.com/1.jpg",
                "https://cdn.example.com/2.jpg",
                "https://cdn.example.com/3.jpg",
            ]
        )
        assert len(category.images) == 3

    def test_category_with_more_than_3_images_rejected(self):
        """Test that more than 3 images raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            BudgetCategoryCreate(
                name="Too many images",
                images=[
                    "https://cdn.example.com/1.jpg",
                    "https://cdn.example.com/2.jpg",
                    "https://cdn.example.com/3.jpg",
                    "https://cdn.example.com/4.jpg",
                ]
            )
        assert "Maximum 3 images" in str(exc_info.value)

    def test_category_with_no_images(self):
        """Test category with no images."""
        category = BudgetCategoryCreate(name="Simple")
        assert category.images is None

    def test_category_with_empty_images_list(self):
        """Test category with empty images list."""
        category = BudgetCategoryCreate(name="Simple", images=[])
        assert category.images == []


# --- BudgetCategoryUpdate Tests ---

class TestBudgetCategoryUpdate:
    def test_update_name(self):
        """Test updating category name."""
        update = BudgetCategoryUpdate(name="New Name")
        data = update.model_dump(exclude_unset=True)
        assert data == {"name": "New Name"}

    def test_update_images(self):
        """Test updating category images."""
        update = BudgetCategoryUpdate(
            images=["https://cdn.example.com/new.jpg"]
        )
        assert len(update.images) == 1

    def test_update_images_too_many_rejected(self):
        """Test that too many images is rejected on update."""
        with pytest.raises(ValidationError):
            BudgetCategoryUpdate(
                images=["a.jpg", "b.jpg", "c.jpg", "d.jpg"]
            )

    def test_empty_update(self):
        """Test empty category update."""
        update = BudgetCategoryUpdate()
        data = update.model_dump(exclude_unset=True)
        assert data == {}


# --- BudgetCreate Tests ---

class TestBudgetCreate:
    def test_create_budget_with_categories(self):
        """Test creating a budget with nested categories and items."""
        budget = BudgetCreate(
            title="Kitchen Renovation",
            description="Full kitchen renovation budget",
            visit_id=uuid4(),
            categories=[
                BudgetCategoryCreate(
                    name="Demolition",
                    order_index=0,
                    items=[
                        BudgetItemCreate(
                            description="Remove cabinets",
                            quantity=Decimal("8.00"),
                            unit_price=Decimal("75.00"),
                        )
                    ]
                ),
                BudgetCategoryCreate(
                    name="Electrical",
                    order_index=1,
                    images=["https://cdn.example.com/panel.jpg"],
                    items=[
                        BudgetItemCreate(
                            description="New wiring",
                            unit="ft",
                            quantity=Decimal("200.00"),
                            unit_price=Decimal("4.50"),
                        ),
                        BudgetItemCreate(
                            description="Outlets",
                            unit="each",
                            quantity=Decimal("12.00"),
                            unit_price=Decimal("85.00"),
                        )
                    ]
                )
            ]
        )

        assert budget.title == "Kitchen Renovation"
        assert len(budget.categories) == 2
        assert budget.categories[0].name == "Demolition"
        assert len(budget.categories[0].items) == 1
        assert budget.categories[1].name == "Electrical"
        assert len(budget.categories[1].items) == 2
        assert budget.categories[1].images == ["https://cdn.example.com/panel.jpg"]

    def test_create_budget_without_categories(self):
        """Test creating a budget with no categories."""
        budget = BudgetCreate(
            title="Empty Budget",
            visit_id=uuid4(),
        )
        assert budget.categories == []

    def test_create_budget_default_status(self):
        """Test that default status is DRAFT."""
        budget = BudgetCreate(
            title="Draft Budget",
            visit_id=uuid4(),
        )
        assert budget.status == BudgetStatus.DRAFT


# --- BudgetUpdate Tests ---

class TestBudgetUpdate:
    def test_update_title(self):
        """Test updating budget title."""
        update = BudgetUpdate(title="Updated Budget Title")
        data = update.model_dump(exclude_unset=True)
        assert data == {"title": "Updated Budget Title"}

    def test_update_status(self):
        """Test updating budget status."""
        update = BudgetUpdate(status=BudgetStatus.PENDING_APPROVAL)
        assert update.status == BudgetStatus.PENDING_APPROVAL


# --- BudgetVersionResponse Tests ---

class TestBudgetVersionResponse:
    def test_version_response(self):
        """Test version response schema."""
        from datetime import datetime

        version = BudgetVersionResponse(
            id=uuid4(),
            budget_id=uuid4(),
            version_number=1,
            snapshot={"title": "Test", "total_amount": "5000.00"},
            notes="First version",
            created_by_user_id=uuid4(),
            created_by_name="Admin User",
            created_at=datetime.utcnow(),
        )
        assert version.version_number == 1
        assert version.snapshot["title"] == "Test"
        assert version.notes == "First version"
        assert version.created_by_name == "Admin User"

    def test_version_list_response(self):
        """Test version list response schema."""
        from datetime import datetime

        version_data = BudgetVersionResponse(
            id=uuid4(),
            budget_id=uuid4(),
            version_number=1,
            snapshot={"title": "Test"},
            created_at=datetime.utcnow(),
        )
        response = BudgetVersionListResponse(
            versions=[version_data],
            total=1,
            skip=0,
            limit=100
        )
        assert len(response.versions) == 1
        assert response.total == 1
