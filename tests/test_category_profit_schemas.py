"""
Tests for CategoryProfit Schemas.

Tests Pydantic validation rules including:
- Auto-calculation of total_price
- Field constraints (ge=0)
- Partial updates
- Response schema construction
"""

import pytest
from decimal import Decimal
from uuid import uuid4
from datetime import datetime
from pydantic import ValidationError

from app.schemas.category_profit import (
    CategoryProfitCreate,
    CategoryProfitUpdate,
    CategoryProfitResponse,
)


# --- CategoryProfitCreate Tests ---

class TestCategoryProfitCreate:
    def test_create_valid(self):
        """Test creating with valid data."""
        profit = CategoryProfitCreate(
            provider_price=Decimal("1000.00"),
            delivery_cost=Decimal("200.00"),
            profit_percentage=Decimal("25.00"),
        )
        assert profit.provider_price == Decimal("1000.00")
        assert profit.delivery_cost == Decimal("200.00")
        assert profit.profit_percentage == Decimal("25.00")

    def test_auto_calculate_total_price(self):
        """Test that total_price is auto-calculated: (provider + delivery) * (1 + profit%/100)."""
        profit = CategoryProfitCreate(
            provider_price=Decimal("1000.00"),
            delivery_cost=Decimal("200.00"),
            profit_percentage=Decimal("25.00"),
        )
        # (1000 + 200) * (1 + 25/100) = 1200 * 1.25 = 1500.00
        assert profit.total_price == Decimal("1500.00")

    def test_auto_calculate_zero_delivery(self):
        """Test calculation with zero delivery cost."""
        profit = CategoryProfitCreate(
            provider_price=Decimal("500.00"),
            delivery_cost=Decimal("0.00"),
            profit_percentage=Decimal("20.00"),
        )
        # (500 + 0) * 1.20 = 600.00
        assert profit.total_price == Decimal("600.00")

    def test_auto_calculate_zero_profit(self):
        """Test calculation with zero profit percentage (cost only)."""
        profit = CategoryProfitCreate(
            provider_price=Decimal("800.00"),
            delivery_cost=Decimal("100.00"),
            profit_percentage=Decimal("0.00"),
        )
        # (800 + 100) * 1.00 = 900.00
        assert profit.total_price == Decimal("900.00")

    def test_auto_calculate_high_profit(self):
        """Test calculation with high profit percentage."""
        profit = CategoryProfitCreate(
            provider_price=Decimal("1000.00"),
            delivery_cost=Decimal("0.00"),
            profit_percentage=Decimal("100.00"),
        )
        # (1000 + 0) * 2.00 = 2000.00
        assert profit.total_price == Decimal("2000.00")

    def test_auto_calculate_decimal_precision(self):
        """Test that total_price is rounded to 2 decimal places."""
        profit = CategoryProfitCreate(
            provider_price=Decimal("333.33"),
            delivery_cost=Decimal("66.67"),
            profit_percentage=Decimal("15.00"),
        )
        # (333.33 + 66.67) * 1.15 = 400.00 * 1.15 = 460.00
        assert profit.total_price == Decimal("460.00")

    def test_delivery_cost_defaults_to_zero(self):
        """Test that delivery_cost defaults to 0 if not provided."""
        profit = CategoryProfitCreate(
            provider_price=Decimal("1000.00"),
            profit_percentage=Decimal("10.00"),
        )
        assert profit.delivery_cost == Decimal("0")
        # (1000 + 0) * 1.10 = 1100.00
        assert profit.total_price == Decimal("1100.00")

    def test_negative_provider_price_rejected(self):
        """Test that negative provider_price is rejected."""
        with pytest.raises(ValidationError):
            CategoryProfitCreate(
                provider_price=Decimal("-100.00"),
                delivery_cost=Decimal("50.00"),
                profit_percentage=Decimal("10.00"),
            )

    def test_negative_delivery_cost_rejected(self):
        """Test that negative delivery_cost is rejected."""
        with pytest.raises(ValidationError):
            CategoryProfitCreate(
                provider_price=Decimal("100.00"),
                delivery_cost=Decimal("-50.00"),
                profit_percentage=Decimal("10.00"),
            )

    def test_negative_profit_percentage_rejected(self):
        """Test that negative profit_percentage is rejected."""
        with pytest.raises(ValidationError):
            CategoryProfitCreate(
                provider_price=Decimal("100.00"),
                delivery_cost=Decimal("50.00"),
                profit_percentage=Decimal("-10.00"),
            )

    def test_zero_provider_price_allowed(self):
        """Test that zero provider_price is allowed."""
        profit = CategoryProfitCreate(
            provider_price=Decimal("0.00"),
            delivery_cost=Decimal("100.00"),
            profit_percentage=Decimal("20.00"),
        )
        assert profit.provider_price == Decimal("0.00")
        # (0 + 100) * 1.20 = 120.00
        assert profit.total_price == Decimal("120.00")


# --- CategoryProfitUpdate Tests ---

class TestCategoryProfitUpdate:
    def test_partial_update_provider_price(self):
        """Test partial update with only provider_price."""
        update = CategoryProfitUpdate(provider_price=Decimal("1500.00"))
        data = update.model_dump(exclude_unset=True)
        assert data == {"provider_price": Decimal("1500.00")}

    def test_partial_update_delivery_cost(self):
        """Test partial update with only delivery_cost."""
        update = CategoryProfitUpdate(delivery_cost=Decimal("250.00"))
        data = update.model_dump(exclude_unset=True)
        assert data == {"delivery_cost": Decimal("250.00")}

    def test_partial_update_profit_percentage(self):
        """Test partial update with only profit_percentage."""
        update = CategoryProfitUpdate(profit_percentage=Decimal("35.00"))
        data = update.model_dump(exclude_unset=True)
        assert data == {"profit_percentage": Decimal("35.00")}

    def test_update_multiple_fields(self):
        """Test updating multiple fields at once."""
        update = CategoryProfitUpdate(
            provider_price=Decimal("2000.00"),
            profit_percentage=Decimal("30.00"),
        )
        data = update.model_dump(exclude_unset=True)
        assert len(data) == 2
        assert data["provider_price"] == Decimal("2000.00")
        assert data["profit_percentage"] == Decimal("30.00")

    def test_empty_update(self):
        """Test empty update (no fields set)."""
        update = CategoryProfitUpdate()
        data = update.model_dump(exclude_unset=True)
        assert data == {}

    def test_negative_values_rejected(self):
        """Test that negative values are rejected on update."""
        with pytest.raises(ValidationError):
            CategoryProfitUpdate(provider_price=Decimal("-100.00"))


# --- CategoryProfitResponse Tests ---

class TestCategoryProfitResponse:
    def test_response_schema(self):
        """Test creating a response schema."""
        response = CategoryProfitResponse(
            id=uuid4(),
            budget_category_id=uuid4(),
            provider_price=Decimal("1000.00"),
            delivery_cost=Decimal("200.00"),
            profit_percentage=Decimal("25.00"),
            total_price=Decimal("1500.00"),
            created_by_user_id=uuid4(),
            created_by_name="Admin User",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert response.provider_price == Decimal("1000.00")
        assert response.total_price == Decimal("1500.00")
        assert response.created_by_name == "Admin User"

    def test_response_without_created_by(self):
        """Test response when created_by is null."""
        response = CategoryProfitResponse(
            id=uuid4(),
            budget_category_id=uuid4(),
            provider_price=Decimal("500.00"),
            delivery_cost=Decimal("50.00"),
            profit_percentage=Decimal("15.00"),
            total_price=Decimal("632.50"),
            created_by_user_id=None,
            created_by_name=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert response.created_by_user_id is None
        assert response.created_by_name is None
