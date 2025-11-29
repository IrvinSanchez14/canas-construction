"""Company Repository - Data Access Layer."""

from typing import Optional
from sqlalchemy.orm import Session

from app.models import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    """Repository for Company entity following Repository Pattern."""

    def __init__(self, db: Session):
        super().__init__(Company, db)

    def get_by_name(self, name: str) -> Optional[Company]:
        """Get company by name."""
        return self.db.query(Company).filter(Company.name == name).first()

    def get_by_email(self, email: str) -> Optional[Company]:
        """Get company by email."""
        return self.db.query(Company).filter(Company.email == email).first()

    def get_active_companies(self, skip: int = 0, limit: int = 100):
        """Get all active companies."""
        return self.get_all(skip=skip, limit=limit, filters={"is_active": True})
