from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Company(BaseModel):
    """Company model for multi-tenant architecture."""

    __tablename__ = "companies"

    name = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="company", cascade="all, delete-orphan")
    clients = relationship("Client", back_populates="company", cascade="all, delete-orphan")
    project_categories = relationship("ProjectCategory", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Company(id={self.id}, name='{self.name}')>"
