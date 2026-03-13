from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Reference(BaseModel):
    """
    Reference model for multi-tenant CRM.

    Each company has many references (customer testimonials/project references).
    """

    __tablename__ = "customer_references"

    client_name = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=False)
    project_description = Column(String(500), nullable=False)
    project_value = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    display_order = Column(Integer, default=0)

    # Foreign key to company for multi-tenant isolation
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    company = relationship("Company", back_populates="references")

    def __repr__(self):
        return f"<Reference(id={self.id}, client_name='{self.client_name}', company_id={self.company_id})>"
