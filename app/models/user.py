from sqlalchemy import Column, String, Boolean, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, Base


# Association table for many-to-many relationship between User and Role
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
)


class User(BaseModel):
    """User model - belongs to a company and can have multiple roles."""

    __tablename__ = "users"

    email = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Foreign key to company for multi-tenant isolation
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    company = relationship("Company", back_populates="users")
    roles = relationship("Role", secondary=user_roles, back_populates="users")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', company_id={self.company_id})>"
