"""
Tests for CategoryProfit Model.

Tests model creation, one-to-one relationship with BudgetCategory,
cascade behavior, and full budget structure integration.
"""

import pytest
from datetime import datetime
from decimal import Decimal

from app.models.budget import Budget, BudgetItem, BudgetStatus
from app.models.budget_category import BudgetCategory
from app.models.category_profit import CategoryProfit
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


# --- CategoryProfit Model Tests ---

def test_create_category_profit(db_session, sample_budget_category, sample_user):
    """Test creating a category profit with all fields."""
    profit = CategoryProfit(
        budget_category_id=sample_budget_category.id,
        provider_price=Decimal("1000.00"),
        delivery_cost=Decimal("200.00"),
        profit_percentage=Decimal("25.00"),
        total_price=Decimal("1500.00"),
        created_by_user_id=sample_user.id
    )
    db_session.add(profit)
    db_session.commit()
    db_session.refresh(profit)

    assert profit.id is not None
    assert profit.budget_category_id == sample_budget_category.id
    assert profit.provider_price == Decimal("1000.00")
    assert profit.delivery_cost == Decimal("200.00")
    assert profit.profit_percentage == Decimal("25.00")
    assert profit.total_price == Decimal("1500.00")
    assert profit.created_by_user_id == sample_user.id
    assert isinstance(profit.created_at, datetime)
    assert isinstance(profit.updated_at, datetime)


def test_create_category_profit_without_created_by(db_session, sample_budget_category):
    """Test creating a category profit without created_by_user_id (nullable)."""
    profit = CategoryProfit(
        budget_category_id=sample_budget_category.id,
        provider_price=Decimal("500.00"),
        delivery_cost=Decimal("50.00"),
        profit_percentage=Decimal("20.00"),
        total_price=Decimal("660.00"),
        created_by_user_id=None
    )
    db_session.add(profit)
    db_session.commit()
    db_session.refresh(profit)

    assert profit.id is not None
    assert profit.created_by_user_id is None


def test_category_profit_zero_delivery_cost(db_session, sample_budget_category):
    """Test profit with zero delivery cost."""
    profit = CategoryProfit(
        budget_category_id=sample_budget_category.id,
        provider_price=Decimal("1000.00"),
        delivery_cost=Decimal("0.00"),
        profit_percentage=Decimal("15.00"),
        total_price=Decimal("1150.00")
    )
    db_session.add(profit)
    db_session.commit()
    db_session.refresh(profit)

    assert profit.delivery_cost == Decimal("0.00")
    assert profit.total_price == Decimal("1150.00")


def test_category_profit_zero_profit_percentage(db_session, sample_budget_category):
    """Test profit with 0% markup (cost-only)."""
    profit = CategoryProfit(
        budget_category_id=sample_budget_category.id,
        provider_price=Decimal("800.00"),
        delivery_cost=Decimal("100.00"),
        profit_percentage=Decimal("0.00"),
        total_price=Decimal("900.00")
    )
    db_session.add(profit)
    db_session.commit()
    db_session.refresh(profit)

    assert profit.profit_percentage == Decimal("0.00")
    assert profit.total_price == Decimal("900.00")


# --- Relationship Tests ---

def test_profit_to_category_relationship(db_session, sample_budget_category):
    """Test CategoryProfit → BudgetCategory forward relationship."""
    profit = CategoryProfit(
        budget_category_id=sample_budget_category.id,
        provider_price=Decimal("500.00"),
        delivery_cost=Decimal("50.00"),
        profit_percentage=Decimal("20.00"),
        total_price=Decimal("660.00")
    )
    db_session.add(profit)
    db_session.commit()
    db_session.refresh(profit)

    assert profit.budget_category is not None
    assert profit.budget_category.id == sample_budget_category.id
    assert profit.budget_category.name == "Demolition"


def test_category_to_profit_relationship(db_session, sample_budget_category):
    """Test BudgetCategory → CategoryProfit reverse relationship (one-to-one)."""
    profit = CategoryProfit(
        budget_category_id=sample_budget_category.id,
        provider_price=Decimal("500.00"),
        delivery_cost=Decimal("50.00"),
        profit_percentage=Decimal("20.00"),
        total_price=Decimal("660.00")
    )
    db_session.add(profit)
    db_session.commit()
    db_session.refresh(sample_budget_category)

    assert sample_budget_category.category_profit is not None
    assert sample_budget_category.category_profit.id == profit.id
    assert sample_budget_category.category_profit.provider_price == Decimal("500.00")


def test_category_without_profit(db_session, sample_budget_category):
    """Test that a category without profit returns None."""
    db_session.refresh(sample_budget_category)
    assert sample_budget_category.category_profit is None


def test_profit_user_relationship(db_session, sample_budget_category, sample_user):
    """Test CategoryProfit → User relationship."""
    profit = CategoryProfit(
        budget_category_id=sample_budget_category.id,
        provider_price=Decimal("500.00"),
        delivery_cost=Decimal("50.00"),
        profit_percentage=Decimal("20.00"),
        total_price=Decimal("660.00"),
        created_by_user_id=sample_user.id
    )
    db_session.add(profit)
    db_session.commit()
    db_session.refresh(profit)

    assert profit.created_by is not None
    assert profit.created_by.id == sample_user.id
    assert profit.created_by.first_name == "Test"


# --- Cascade Tests ---

def test_profit_cascade_delete_with_category(db_session, sample_budget_category):
    """Test that profit is deleted when category is deleted."""
    profit = CategoryProfit(
        budget_category_id=sample_budget_category.id,
        provider_price=Decimal("1000.00"),
        delivery_cost=Decimal("200.00"),
        profit_percentage=Decimal("25.00"),
        total_price=Decimal("1500.00")
    )
    db_session.add(profit)
    db_session.commit()

    profit_id = profit.id

    # Delete category
    db_session.delete(sample_budget_category)
    db_session.commit()

    deleted = db_session.query(CategoryProfit).filter(
        CategoryProfit.id == profit_id
    ).first()
    assert deleted is None


def test_profit_cascade_delete_with_budget(db_session, sample_budget):
    """Test full cascade: deleting budget deletes categories and their profits."""
    category = BudgetCategory(
        name="Electrical",
        order_index=0,
        subtotal=Decimal("0"),
        budget_id=sample_budget.id
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    profit = CategoryProfit(
        budget_category_id=category.id,
        provider_price=Decimal("800.00"),
        delivery_cost=Decimal("100.00"),
        profit_percentage=Decimal("30.00"),
        total_price=Decimal("1170.00")
    )
    db_session.add(profit)
    db_session.commit()

    cat_id = category.id
    profit_id = profit.id

    # Delete budget
    db_session.delete(sample_budget)
    db_session.commit()

    assert db_session.query(BudgetCategory).filter(BudgetCategory.id == cat_id).first() is None
    assert db_session.query(CategoryProfit).filter(CategoryProfit.id == profit_id).first() is None


def test_profit_user_set_null_on_delete(db_session, sample_budget_category, sample_user):
    """Test that profit persists when user is deleted.

    Note: ON DELETE SET NULL is enforced by PostgreSQL in production.
    SQLite test DB does not enforce FK actions, so we only verify
    the profit record still exists after user deletion.
    """
    profit = CategoryProfit(
        budget_category_id=sample_budget_category.id,
        provider_price=Decimal("500.00"),
        delivery_cost=Decimal("50.00"),
        profit_percentage=Decimal("20.00"),
        total_price=Decimal("660.00"),
        created_by_user_id=sample_user.id
    )
    db_session.add(profit)
    db_session.commit()

    profit_id = profit.id

    # Delete user
    db_session.delete(sample_user)
    db_session.commit()

    # Profit should still exist (not cascade deleted)
    existing = db_session.query(CategoryProfit).filter(
        CategoryProfit.id == profit_id
    ).first()
    assert existing is not None


# --- Repr Test ---

def test_category_profit_repr(db_session, sample_budget_category):
    """Test string representation."""
    profit = CategoryProfit(
        budget_category_id=sample_budget_category.id,
        provider_price=Decimal("1000.00"),
        delivery_cost=Decimal("200.00"),
        profit_percentage=Decimal("25.00"),
        total_price=Decimal("1500.00")
    )
    db_session.add(profit)
    db_session.commit()
    db_session.refresh(profit)

    repr_str = repr(profit)
    assert "CategoryProfit" in repr_str
    assert "1500" in repr_str


# --- Full Integration Test ---

def test_full_budget_with_profits(db_session, sample_visit, sample_user):
    """Test complete structure: Budget → Categories → Items + Profits."""
    # Create budget
    budget = Budget(
        title="Full Renovation Budget",
        status=BudgetStatus.DRAFT,
        total_amount=Decimal("0"),
        current_version=0,
        visit_id=sample_visit.id
    )
    db_session.add(budget)
    db_session.commit()
    db_session.refresh(budget)

    # Create categories
    demo_cat = BudgetCategory(
        name="Demolition",
        order_index=0,
        subtotal=Decimal("0"),
        budget_id=budget.id
    )
    elec_cat = BudgetCategory(
        name="Electrical",
        order_index=1,
        subtotal=Decimal("0"),
        budget_id=budget.id
    )
    db_session.add_all([demo_cat, elec_cat])
    db_session.commit()
    db_session.refresh(demo_cat)
    db_session.refresh(elec_cat)

    # Add profit to Demolition: (800 + 100) * 1.20 = 1080
    demo_profit = CategoryProfit(
        budget_category_id=demo_cat.id,
        provider_price=Decimal("800.00"),
        delivery_cost=Decimal("100.00"),
        profit_percentage=Decimal("20.00"),
        total_price=Decimal("1080.00"),
        created_by_user_id=sample_user.id
    )
    # Add profit to Electrical: (2000 + 300) * 1.25 = 2875
    elec_profit = CategoryProfit(
        budget_category_id=elec_cat.id,
        provider_price=Decimal("2000.00"),
        delivery_cost=Decimal("300.00"),
        profit_percentage=Decimal("25.00"),
        total_price=Decimal("2875.00"),
        created_by_user_id=sample_user.id
    )
    db_session.add_all([demo_profit, elec_profit])

    # Sync subtotals
    demo_cat.subtotal = Decimal("1080.00")
    elec_cat.subtotal = Decimal("2875.00")
    budget.total_amount = Decimal("3955.00")
    db_session.commit()

    # Verify full structure
    db_session.refresh(budget)

    assert budget.total_amount == Decimal("3955.00")
    assert len(budget.budget_categories) == 2

    # Verify Demolition
    assert budget.budget_categories[0].name == "Demolition"
    assert budget.budget_categories[0].category_profit is not None
    assert budget.budget_categories[0].category_profit.provider_price == Decimal("800.00")
    assert budget.budget_categories[0].category_profit.total_price == Decimal("1080.00")
    assert budget.budget_categories[0].subtotal == Decimal("1080.00")

    # Verify Electrical
    assert budget.budget_categories[1].name == "Electrical"
    assert budget.budget_categories[1].category_profit is not None
    assert budget.budget_categories[1].category_profit.provider_price == Decimal("2000.00")
    assert budget.budget_categories[1].category_profit.total_price == Decimal("2875.00")
    assert budget.budget_categories[1].subtotal == Decimal("2875.00")


def test_category_with_both_items_and_profit(db_session, sample_budget_category):
    """Test that a category can have both items and profit data."""
    # Add items
    item = BudgetItem(
        description="Remove drywall",
        unit="sq ft",
        quantity=Decimal("500.00"),
        unit_price=Decimal("3.50"),
        subtotal=Decimal("1750.00"),
        order_index=0,
        budget_category_id=sample_budget_category.id
    )
    db_session.add(item)

    # Add profit
    profit = CategoryProfit(
        budget_category_id=sample_budget_category.id,
        provider_price=Decimal("1200.00"),
        delivery_cost=Decimal("150.00"),
        profit_percentage=Decimal("30.00"),
        total_price=Decimal("1755.00")
    )
    db_session.add(profit)
    db_session.commit()
    db_session.refresh(sample_budget_category)

    # Both should coexist
    assert len(sample_budget_category.budget_items) == 1
    assert sample_budget_category.category_profit is not None
    assert sample_budget_category.budget_items[0].subtotal == Decimal("1750.00")
    assert sample_budget_category.category_profit.total_price == Decimal("1755.00")
