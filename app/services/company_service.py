"""
Improved Company Service following SOLID principles.

Changes from original:
- Removed static methods (OCP, DIP)
- Uses dependency injection (DIP)
- Depends on repository abstraction (DIP)
- Single responsibility - only business logic (SRP)
- Proper logging
- Custom exceptions
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import Company
from app.repositories import CompanyRepository
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.core.exceptions import NotFoundException, AlreadyExistsException
from app.core.logging import get_logger

logger = get_logger(__name__)


class CompanyService:
    """
    Service layer for Company business logic.

    Follows SOLID principles:
    - Single Responsibility: Only handles business logic
    - Open/Closed: Can be extended without modification
    - Liskov Substitution: Can be substituted by subclasses
    - Interface Segregation: Minimal interface
    - Dependency Inversion: Depends on abstraction (repository)
    """

    def __init__(self, repository: CompanyRepository):
        """
        Initialize service with injected dependencies.

        Args:
            repository: Company repository (injected)
        """
        self.repository = repository

    def create_company(self, company_data: CompanyCreate) -> Company:
        """
        Create a new company.

        Business Rules:
        - Company name must be unique
        - Company email must be unique

        Args:
            company_data: Company creation data

        Returns:
            Created company

        Raises:
            AlreadyExistsException: If company with name or email exists
        """
        logger.info(f"Creating company: {company_data.name}")

        # Business validation
        if self.repository.get_by_name(company_data.name):
            raise AlreadyExistsException("Company", "name", company_data.name)

        if self.repository.get_by_email(company_data.email):
            raise AlreadyExistsException("Company", "email", company_data.email)

        # Create company
        company = self.repository.create(
            name=company_data.name,
            email=company_data.email,
            phone=company_data.phone,
            address=company_data.address
        )

        logger.info(f"Company created successfully: {company.id}")
        return company

    def get_company(self, company_id: int) -> Company:
        """
        Get company by ID.

        Args:
            company_id: Company ID

        Returns:
            Company

        Raises:
            NotFoundException: If company not found
        """
        return self.repository.get_by_id_or_fail(company_id)

    def get_companies(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[Company]:
        """
        Get all companies with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            is_active: Filter by active status

        Returns:
            List of companies
        """
        filters = {}
        if is_active is not None:
            filters["is_active"] = is_active

        return self.repository.get_all(skip=skip, limit=limit, filters=filters)

    def update_company(self, company_id: int, company_data: CompanyUpdate) -> Company:
        """
        Update company.

        Business Rules:
        - Company name must remain unique (if changed)
        - Company email must remain unique (if changed)

        Args:
            company_id: Company ID
            company_data: Update data

        Returns:
            Updated company

        Raises:
            NotFoundException: If company not found
            AlreadyExistsException: If name/email conflict
        """
        logger.info(f"Updating company: {company_id}")

        company = self.repository.get_by_id_or_fail(company_id)

        update_data = company_data.model_dump(exclude_unset=True)

        # Validate unique name
        if "name" in update_data and update_data["name"] != company.name:
            if self.repository.get_by_name(update_data["name"]):
                raise AlreadyExistsException("Company", "name", update_data["name"])

        # Validate unique email
        if "email" in update_data and update_data["email"] != company.email:
            if self.repository.get_by_email(update_data["email"]):
                raise AlreadyExistsException("Company", "email", update_data["email"])

        # Update
        updated_company = self.repository.update(company, **update_data)
        logger.info(f"Company updated successfully: {company_id}")

        return updated_company

    def delete_company(self, company_id: int) -> None:
        """
        Delete company (cascade deletes users and roles).

        Args:
            company_id: Company ID

        Raises:
            NotFoundException: If company not found
        """
        logger.warning(f"Deleting company: {company_id}")

        company = self.repository.get_by_id_or_fail(company_id)
        self.repository.delete(company)

        logger.info(f"Company deleted successfully: {company_id}")

    def count_companies(self, is_active: Optional[bool] = None) -> int:
        """
        Count companies.

        Args:
            is_active: Filter by active status

        Returns:
            Total count
        """
        filters = {}
        if is_active is not None:
            filters["is_active"] = is_active

        return self.repository.count(filters=filters)
