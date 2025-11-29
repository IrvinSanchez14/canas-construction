"""User Repository - Data Access Layer."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload

from app.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User entity following Repository Pattern."""

    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email with roles eagerly loaded (N+1 optimization)."""
        return self.db.query(User).options(
            joinedload(User.roles)
        ).filter(User.email == email).first()

    def get_by_id_with_roles(self, user_id: int) -> Optional[User]:
        """Get user by ID with roles eagerly loaded (N+1 optimization)."""
        return self.db.query(User).options(
            joinedload(User.roles)
        ).filter(User.id == user_id).first()

    def get_by_company(
        self,
        company_id: int,
        skip: int = 0,
        limit: int = 100,
        include_roles: bool = True
    ) -> List[User]:
        """
        Get all users for a specific company.

        Args:
            company_id: Company ID filter
            skip: Pagination offset
            limit: Pagination limit
            include_roles: Whether to eager load roles (prevents N+1)
        """
        query = self.db.query(User).filter(User.company_id == company_id)

        if include_roles:
            query = query.options(joinedload(User.roles))

        return query.offset(skip).limit(limit).all()

    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()

    def get_active_users_by_company(self, company_id: int) -> List[User]:
        """Get all active users for a company."""
        return self.db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).all()

    def exists_by_email(self, email: str, exclude_id: Optional[int] = None) -> bool:
        """Check if email exists (optionally excluding a specific user ID)."""
        query = self.db.query(User.id).filter(User.email == email)

        if exclude_id:
            query = query.filter(User.id != exclude_id)

        return query.first() is not None

    def get_superusers(self) -> List[User]:
        """Get all superusers."""
        return self.db.query(User).filter(User.is_superuser == True).all()
