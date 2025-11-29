from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Client(BaseModel):
    """
    Client model for multi-tenant CRM.

    Each company has many clients (construction customers).
    Each client can have multiple projects.
    """

    __tablename__ = "clients"

    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)

    # Foreign key to company for multi-tenant isolation
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    company = relationship("Company", back_populates="clients")
    projects = relationship("Project", back_populates="client", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.name}', company_id={self.company_id})>"
