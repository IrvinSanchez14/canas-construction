"""Role Repository - Data Access Layer."""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import Role
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Repository for Role entity following Repository Pattern."""

    def __init__(self, db: Session):
        super().__init__(Role, db)

    def get_by_company(self, company_id: int, skip: int = 0, limit: int = 100) -> List[Role]:
        """Get all roles for a specific company."""
        return self.get_all(skip=skip, limit=limit, filters={"company_id": company_id})

    def get_by_name_and_company(self, name: str, company_id: int) -> Optional[Role]:
        """Get role by name within a specific company."""
        return self.db.query(Role).filter(
            Role.name == name,
            Role.company_id == company_id
        ).first()

    def get_active_roles_by_company(self, company_id: int) -> List[Role]:
        """Get all active roles for a company."""
        return self.db.query(Role).filter(
            Role.company_id == company_id,
            Role.is_active == True
        ).all()

    def exists_in_company(self, name: str, company_id: int, exclude_id: Optional[int] = None) -> bool:
        """Check if role name exists in company (optionally excluding a specific ID)."""
        query = self.db.query(Role.id).filter(
            Role.name == name,
            Role.company_id == company_id
        )

        if exclude_id:
            query = query.filter(Role.id != exclude_id)

        return query.first() is not None
