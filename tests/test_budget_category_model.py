"""
Tests for BudgetCategory Model and updated Budget → Categories → Items structure.

Tests model creation, relationships, cascade behavior, and versioning.
"""

import pytest
import json
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.models.budget import Budget, BudgetItem, BudgetStatus
from app.models.budget_category import BudgetCategory
from app.models.budget_version import BudgetVersion
from app.models.visit import Visit, VisitStatus
from app.models.project import Project, ProjectStatus
from app.models.client import Client
from app.models.project_category import ProjectCategory
from app.models.user import User
from app.models.company import Company


# --- Fixtures ---

@pytest.fixture
def sample_company(db_session):
    """Create a sample company."""
    company = Company(
        name="Test Construction Co",
        email="test@construction.com",
        phone="555-0000",
        address="123 Builder St"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def sample_user(db_session, sample_company):
    """Create a sample user."""
    user = User(
        email="admin@construction.com",
        username="testadmin",
        hashed_password="hashedpassword",
        first_name="Test",
        last_name="Admin",
        company_id=sample_company.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_client(db_session, sample_company):
    """Create a sample client."""
    client = Client(
        name="Test Client",
        email="client@example.com",
        phone="555-1234",
        company_id=sample_company.id
    )
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


@pytest.fixture
def sample_category(db_session, sample_company):
    """Create a sample project category."""
    category = ProjectCategory(
        name="Residential",
        description="Residential projects",
        company_id=sample_company.id
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def sample_project(db_session, sample_client, sample_category, sample_user):
    """Create a sample project."""
    project = Project(
        name="Test Renovation",
        description="Kitchen renovation project",
        status=ProjectStatus.IN_PROGRESS,
        client_id=sample_client.id,
        category_id=sample_category.id,
        created_by_user_id=sample_user.id
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def sample_visit(db_session, sample_project, sample_user):
    """Create a sample visit."""
    visit = Visit(
        title="Initial Site Visit",
        description="First visit to assess the property",
        status=VisitStatus.PLANNING,
        project_id=sample_project.id,
        created_by_user_id=sample_user.id
    )
    db_session.add(visit)
    db_session.commit()
    db_session.refresh(visit)
    return visit


@pytest.fixture
def sample_budget(db_session, sample_visit):
    """Create a sample budget."""
    budget = Budget(
        title="Kitchen Renovation Budget",
        description="Full budget for kitchen renovation",
        status=BudgetStatus.DRAFT,
        total_amount=Decimal("0"),
        current_version=0,
        visit_id=sample_visit.id
    )
    db_session.add(budget)
    db_session.commit()
    db_session.refresh(budget)
    return budget


@pytest.fixture
def sample_budget_category(db_session, sample_budget):
    """Create a sample budget category."""
    category = BudgetCategory(
        name="Demolition",
        description="Demo work for existing structures",
        images=None,
        order_index=0,
        subtotal=Decimal("0"),
        budget_id=sample_budget.id
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


# --- BudgetCategory Model Tests ---

def test_create_budget_category(db_session, sample_budget):
    """Test creating a budget category."""
    category = BudgetCategory(
        name="Electrical",
        description="All electrical work including wiring and panels",
        images=["https://cdn.example.com/img1.jpg", "https://cdn.example.com/img2.jpg"],
        order_index=1,
        subtotal=Decimal("2500.00"),
        budget_id=sample_budget.id
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    assert category.id is not None
    assert category.name == "Electrical"
    assert category.description == "All electrical work including wiring and panels"
    assert category.images == ["https://cdn.example.com/img1.jpg", "https://cdn.example.com/img2.jpg"]
    assert category.order_index == 1
    assert category.subtotal == Decimal("2500.00")
    assert category.budget_id == sample_budget.id
    assert isinstance(category.created_at, datetime)
    assert isinstance(category.updated_at, datetime)


def test_create_category_without_optional_fields(db_session, sample_budget):
    """Test creating a category with only required fields."""
    category = BudgetCategory(
        name="Plumbing",
        order_index=0,
        subtotal=Decimal("0"),
        budget_id=sample_budget.id
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    assert category.id is not None
    assert category.name == "Plumbing"
    assert category.description is None
    assert category.images is None


def test_category_with_images(db_session, sample_budget):
    """Test category with up to 3 images."""
    images = [
        "https://cdn.example.com/demo1.jpg",
        "https://cdn.example.com/demo2.jpg",
        "https://cdn.example.com/demo3.jpg"
    ]
    category = BudgetCategory(
        name="Demolition",
        images=images,
        order_index=0,
        subtotal=Decimal("0"),
        budget_id=sample_budget.id
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    assert len(category.images) == 3
    assert category.images[0] == "https://cdn.example.com/demo1.jpg"


def test_category_budget_relationship(db_session, sample_budget):
    """Test category → budget relationship."""
    category = BudgetCategory(
        name="Painting",
        order_index=0,
        subtotal=Decimal("0"),
        budget_id=sample_budget.id
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    # Forward relationship
    assert category.budget is not None
    assert category.budget.id == sample_budget.id
    assert category.budget.title == "Kitchen Renovation Budget"

    # Backward relationship
    db_session.refresh(sample_budget)
    assert len(sample_budget.budget_categories) == 1
    assert sample_budget.budget_categories[0].id == category.id


def test_multiple_categories_per_budget(db_session, sample_budget):
    """Test adding multiple categories to a budget."""
    category_names = ["Demolition", "Electrical", "Plumbing", "Painting", "Flooring"]
    for idx, name in enumerate(category_names):
        cat = BudgetCategory(
            name=name,
            order_index=idx,
            subtotal=Decimal("0"),
            budget_id=sample_budget.id
        )
        db_session.add(cat)

    db_session.commit()
    db_session.refresh(sample_budget)

    assert len(sample_budget.budget_categories) == 5


def test_category_cascade_delete_with_budget(db_session, sample_budget):
    """Test that categories are deleted when budget is deleted."""
    category = BudgetCategory(
        name="Demo",
        order_index=0,
        subtotal=Decimal("0"),
        budget_id=sample_budget.id
    )
    db_session.add(category)
    db_session.commit()

    category_id = category.id

    # Delete budget
    db_session.delete(sample_budget)
    db_session.commit()

    deleted = db_session.query(BudgetCategory).filter(
        BudgetCategory.id == category_id
    ).first()
    assert deleted is None


def test_category_repr(db_session, sample_budget):
    """Test category string representation."""
    category = BudgetCategory(
        name="Electrical",
        order_index=0,
        subtotal=Decimal("0"),
        budget_id=sample_budget.id
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    repr_str = repr(category)
    assert "BudgetCategory" in repr_str
    assert "Electrical" in repr_str


# --- BudgetItem within Category Tests ---

def test_create_item_in_category(db_session, sample_budget_category):
    """Test creating a budget item within a category."""
    item = BudgetItem(
        description="Remove existing drywall in kitchen area",
        unit="sq ft",
        quantity=Decimal("500.00"),
        unit_price=Decimal("3.50"),
        subtotal=Decimal("1750.00"),
        order_index=0,
        budget_category_id=sample_budget_category.id
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    assert item.id is not None
    assert item.description == "Remove existing drywall in kitchen area"
    assert item.unit == "sq ft"
    assert item.quantity == Decimal("500.00")
    assert item.unit_price == Decimal("3.50")
    assert item.subtotal == Decimal("1750.00")
    assert item.budget_category_id == sample_budget_category.id


def test_item_category_relationship(db_session, sample_budget_category):
    """Test item → category relationship."""
    item = BudgetItem(
        description="Haul debris",
        unit="load",
        quantity=Decimal("3.00"),
        unit_price=Decimal("250.00"),
        subtotal=Decimal("750.00"),
        order_index=0,
        budget_category_id=sample_budget_category.id
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    # Forward relationship
    assert item.budget_category is not None
    assert item.budget_category.id == sample_budget_category.id
    assert item.budget_category.name == "Demolition"

    # Backward relationship
    db_session.refresh(sample_budget_category)
    assert len(sample_budget_category.budget_items) == 1
    assert sample_budget_category.budget_items[0].id == item.id


def test_multiple_items_per_category(db_session, sample_budget_category):
    """Test adding multiple items to a category."""
    for i in range(5):
        item = BudgetItem(
            description=f"Demo item {i}",
            unit="each",
            quantity=Decimal(str(i + 1)),
            unit_price=Decimal("100.00"),
            subtotal=Decimal(str((i + 1) * 100)),
            order_index=i,
            budget_category_id=sample_budget_category.id
        )
        db_session.add(item)

    db_session.commit()
    db_session.refresh(sample_budget_category)

    assert len(sample_budget_category.budget_items) == 5


def test_item_cascade_delete_with_category(db_session, sample_budget_category):
    """Test that items are deleted when category is deleted."""
    item = BudgetItem(
        description="Test item",
        unit="each",
        quantity=Decimal("1.00"),
        unit_price=Decimal("50.00"),
        subtotal=Decimal("50.00"),
        order_index=0,
        budget_category_id=sample_budget_category.id
    )
    db_session.add(item)
    db_session.commit()

    item_id = item.id

    # Delete category
    db_session.delete(sample_budget_category)
    db_session.commit()

    deleted = db_session.query(BudgetItem).filter(
        BudgetItem.id == item_id
    ).first()
    assert deleted is None


def test_full_cascade_budget_to_items(db_session, sample_budget):
    """Test full cascade: deleting budget deletes categories and items."""
    category = BudgetCategory(
        name="Electrical",
        order_index=0,
        subtotal=Decimal("500.00"),
        budget_id=sample_budget.id
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    item = BudgetItem(
        description="Install outlets",
        unit="each",
        quantity=Decimal("10.00"),
        unit_price=Decimal("50.00"),
        subtotal=Decimal("500.00"),
        order_index=0,
        budget_category_id=category.id
    )
    db_session.add(item)
    db_session.commit()

    cat_id = category.id
    item_id = item.id

    # Delete budget
    db_session.delete(sample_budget)
    db_session.commit()

    assert db_session.query(BudgetCategory).filter(BudgetCategory.id == cat_id).first() is None
    assert db_session.query(BudgetItem).filter(BudgetItem.id == item_id).first() is None


# --- Budget Model Updated Fields Tests ---

def test_budget_current_version_field(db_session, sample_visit):
    """Test budget has current_version field."""
    budget = Budget(
        title="Test Budget",
        status=BudgetStatus.DRAFT,
        total_amount=Decimal("0"),
        current_version=0,
        visit_id=sample_visit.id
    )
    db_session.add(budget)
    db_session.commit()
    db_session.refresh(budget)

    assert budget.current_version == 0


def test_budget_categories_relationship(db_session, sample_budget):
    """Test budget → categories relationship ordering."""
    for idx, name in enumerate(["Plumbing", "Electrical", "Demolition"]):
        cat = BudgetCategory(
            name=name,
            order_index=idx,
            subtotal=Decimal("0"),
            budget_id=sample_budget.id
        )
        db_session.add(cat)

    db_session.commit()
    db_session.refresh(sample_budget)

    assert len(sample_budget.budget_categories) == 3
    assert sample_budget.budget_categories[0].name == "Plumbing"
    assert sample_budget.budget_categories[1].name == "Electrical"
    assert sample_budget.budget_categories[2].name == "Demolition"


# --- BudgetVersion Model Tests ---

def test_create_budget_version(db_session, sample_budget, sample_user):
    """Test creating a budget version snapshot."""
    snapshot = {
        "title": "Kitchen Renovation Budget",
        "description": "Full budget",
        "status": "draft",
        "total_amount": "5000.00",
        "categories": [
            {
                "name": "Demolition",
                "items": [
                    {"description": "Remove drywall", "quantity": "500", "unit_price": "3.50", "subtotal": "1750.00"}
                ]
            }
        ]
    }

    version = BudgetVersion(
        budget_id=sample_budget.id,
        version_number=1,
        snapshot=snapshot,
        notes="Initial version",
        created_by_user_id=sample_user.id
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    assert version.id is not None
    assert version.budget_id == sample_budget.id
    assert version.version_number == 1
    assert version.snapshot["title"] == "Kitchen Renovation Budget"
    assert version.notes == "Initial version"
    assert version.created_by_user_id == sample_user.id
    assert isinstance(version.created_at, datetime)


def test_multiple_versions(db_session, sample_budget, sample_user):
    """Test creating multiple versions for a budget."""
    for i in range(1, 4):
        version = BudgetVersion(
            budget_id=sample_budget.id,
            version_number=i,
            snapshot={"title": f"Version {i}", "total_amount": str(i * 1000)},
            notes=f"Version {i} notes",
            created_by_user_id=sample_user.id
        )
        db_session.add(version)

    db_session.commit()
    db_session.refresh(sample_budget)

    assert len(sample_budget.versions) == 3
    assert sample_budget.versions[0].version_number == 1
    assert sample_budget.versions[2].version_number == 3


def test_version_budget_relationship(db_session, sample_budget, sample_user):
    """Test version → budget relationship."""
    version = BudgetVersion(
        budget_id=sample_budget.id,
        version_number=1,
        snapshot={"title": "Test"},
        created_by_user_id=sample_user.id
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    assert version.budget is not None
    assert version.budget.id == sample_budget.id


def test_version_user_relationship(db_session, sample_budget, sample_user):
    """Test version → user relationship."""
    version = BudgetVersion(
        budget_id=sample_budget.id,
        version_number=1,
        snapshot={"title": "Test"},
        created_by_user_id=sample_user.id
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    assert version.created_by is not None
    assert version.created_by.id == sample_user.id
    assert version.created_by.first_name == "Test"


def test_version_cascade_delete_with_budget(db_session, sample_budget, sample_user):
    """Test that versions are deleted when budget is deleted."""
    version = BudgetVersion(
        budget_id=sample_budget.id,
        version_number=1,
        snapshot={"title": "Test"},
        created_by_user_id=sample_user.id
    )
    db_session.add(version)
    db_session.commit()

    version_id = version.id

    db_session.delete(sample_budget)
    db_session.commit()

    deleted = db_session.query(BudgetVersion).filter(
        BudgetVersion.id == version_id
    ).first()
    assert deleted is None


def test_version_user_set_null_on_delete(db_session, sample_budget, sample_user):
    """Test that version persists when user is deleted.

    Note: ON DELETE SET NULL is enforced by PostgreSQL in production.
    SQLite test DB does not enforce FK actions, so we only verify
    the version record still exists after user deletion.
    """
    version = BudgetVersion(
        budget_id=sample_budget.id,
        version_number=1,
        snapshot={"title": "Test"},
        created_by_user_id=sample_user.id
    )
    db_session.add(version)
    db_session.commit()

    version_id = version.id

    # Delete user
    db_session.delete(sample_user)
    db_session.commit()

    # Version should still exist (not cascade deleted)
    version = db_session.query(BudgetVersion).filter(
        BudgetVersion.id == version_id
    ).first()
    assert version is not None


def test_version_without_notes(db_session, sample_budget):
    """Test creating a version without notes."""
    version = BudgetVersion(
        budget_id=sample_budget.id,
        version_number=1,
        snapshot={"title": "Test"},
        notes=None
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    assert version.notes is None


def test_version_repr(db_session, sample_budget):
    """Test version string representation."""
    version = BudgetVersion(
        budget_id=sample_budget.id,
        version_number=1,
        snapshot={"title": "Test"}
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    repr_str = repr(version)
    assert "BudgetVersion" in repr_str


# --- Full Integration: Budget → Categories → Items → Versions ---

def test_full_budget_structure(db_session, sample_visit, sample_user):
    """Test complete Budget → Categories → Items structure."""
    # Create budget
    budget = Budget(
        title="Full Renovation Budget",
        description="Complete renovation budget with multiple categories",
        status=BudgetStatus.DRAFT,
        total_amount=Decimal("0"),
        current_version=0,
        visit_id=sample_visit.id
    )
    db_session.add(budget)
    db_session.commit()
    db_session.refresh(budget)

    # Create categories with items
    demo_cat = BudgetCategory(
        name="Demolition",
        description="Removal of existing structures",
        images=["https://cdn.example.com/demo1.jpg"],
        order_index=0,
        subtotal=Decimal("0"),
        budget_id=budget.id
    )
    db_session.add(demo_cat)
    db_session.commit()
    db_session.refresh(demo_cat)

    electrical_cat = BudgetCategory(
        name="Electrical",
        description="All electrical work",
        images=["https://cdn.example.com/elec1.jpg", "https://cdn.example.com/elec2.jpg"],
        order_index=1,
        subtotal=Decimal("0"),
        budget_id=budget.id
    )
    db_session.add(electrical_cat)
    db_session.commit()
    db_session.refresh(electrical_cat)

    # Add items to Demolition
    item1 = BudgetItem(
        description="Remove kitchen cabinets",
        unit="each",
        quantity=Decimal("8.00"),
        unit_price=Decimal("75.00"),
        subtotal=Decimal("600.00"),
        order_index=0,
        budget_category_id=demo_cat.id
    )
    item2 = BudgetItem(
        description="Remove flooring",
        unit="sq ft",
        quantity=Decimal("200.00"),
        unit_price=Decimal("2.50"),
        subtotal=Decimal("500.00"),
        order_index=1,
        budget_category_id=demo_cat.id
    )
    db_session.add_all([item1, item2])

    # Add items to Electrical
    item3 = BudgetItem(
        description="Install new outlets",
        unit="each",
        quantity=Decimal("12.00"),
        unit_price=Decimal("85.00"),
        subtotal=Decimal("1020.00"),
        order_index=0,
        budget_category_id=electrical_cat.id
    )
    db_session.add(item3)
    db_session.commit()

    # Update subtotals
    demo_cat.subtotal = Decimal("1100.00")
    electrical_cat.subtotal = Decimal("1020.00")
    budget.total_amount = Decimal("2120.00")
    db_session.commit()

    # Create a version
    version = BudgetVersion(
        budget_id=budget.id,
        version_number=1,
        snapshot={
            "title": budget.title,
            "total_amount": "2120.00",
            "categories": [
                {"name": "Demolition", "subtotal": "1100.00", "items": 2},
                {"name": "Electrical", "subtotal": "1020.00", "items": 1}
            ]
        },
        notes="First draft",
        created_by_user_id=sample_user.id
    )
    db_session.add(version)
    budget.current_version = 1
    db_session.commit()

    # Verify full structure
    db_session.refresh(budget)

    assert budget.total_amount == Decimal("2120.00")
    assert budget.current_version == 1
    assert len(budget.budget_categories) == 2
    assert len(budget.versions) == 1

    # Verify Demo category
    assert budget.budget_categories[0].name == "Demolition"
    assert len(budget.budget_categories[0].budget_items) == 2
    assert budget.budget_categories[0].subtotal == Decimal("1100.00")

    # Verify Electrical category
    assert budget.budget_categories[1].name == "Electrical"
    assert len(budget.budget_categories[1].budget_items) == 1
    assert budget.budget_categories[1].subtotal == Decimal("1020.00")

    # Verify version
    assert budget.versions[0].version_number == 1
    assert budget.versions[0].snapshot["total_amount"] == "2120.00"
