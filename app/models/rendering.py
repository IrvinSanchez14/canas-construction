from sqlalchemy import Column, String, ForeignKey, Text, Enum, Numeric, Integer, DateTime, Boolean, Date
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


class RenderingStatus(enum.Enum):
    """Enum for rendering status in the construction workflow."""
    DRAFT = "draft"  # Rendering being created/edited
    SENT = "sent"  # Rendering sent to client
    APPROVED = "approved"  # Rendering approved by client
    REJECTED = "rejected"  # Rendering rejected by client


class Rendering(BaseModel):
    """
    Rendering model for visual project proposals.

    A rendering is a visual proposal document that contains:
    - 3D rendered images (uploaded by admin, created externally)
    - Material samples with images
    - Item details with specifications and pricing

    Can be generated as a PDF for client presentation.
    """

    __tablename__ = "renderings"

    # Basic information
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    expiration_date = Column(Date, nullable=True)
    status = Column(
        Enum(RenderingStatus, values_callable=lambda x: [e.value for e in x]),
        default=RenderingStatus.DRAFT,
        nullable=False,
        index=True
    )

    # Financial (calculated from items)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)

    # Version tracking
    current_version = Column(Integer, nullable=False, default=0)

    # Foreign key to project
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Foreign key to visit (optional)
    visit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("visits.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Foreign key to budget (optional, can import items from budget)
    budget_id = Column(
        UUID(as_uuid=True),
        ForeignKey("budgets.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Sent tracking
    sent_at = Column(DateTime, nullable=True)
    sent_to_email = Column(String(255), nullable=True)

    # Approval tracking
    approved_at = Column(DateTime, nullable=True)
    approved_by_client_name = Column(String(255), nullable=True)

    # Relationships
    project = relationship("Project", foreign_keys=[project_id])
    visit = relationship("Visit", foreign_keys=[visit_id])
    budget = relationship("Budget", foreign_keys=[budget_id])
    images = relationship(
        "RenderingImage",
        back_populates="rendering",
        cascade="all, delete-orphan",
        order_by="RenderingImage.display_order"
    )
    items = relationship(
        "RenderingItem",
        back_populates="rendering",
        cascade="all, delete-orphan",
        order_by="RenderingItem.order_index"
    )
    versions = relationship(
        "RenderingVersion",
        back_populates="rendering",
        cascade="all, delete-orphan",
        order_by="RenderingVersion.version_number.desc()"
    )

    def __repr__(self):
        return f"<Rendering(id={self.id}, title='{self.title}', status={self.status})>"


class RenderingImage(BaseModel):
    """
    Rendering Image model for 3D rendered images and material samples.

    Images are uploaded by admin (created externally in 3D software).
    Can be marked as full-page for PDF generation.
    """

    __tablename__ = "rendering_images"

    # Image details
    image_url = Column(String(500), nullable=False)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Display settings
    display_order = Column(Integer, nullable=False, default=0)
    is_full_page = Column(Boolean, nullable=False, default=False)

    # Image type: 'project' for 3D renders, 'material' for material samples
    image_type = Column(String(50), nullable=False, default='project')

    # Foreign key to rendering
    rendering_id = Column(
        UUID(as_uuid=True),
        ForeignKey("renderings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    rendering = relationship("Rendering", back_populates="images")

    def __repr__(self):
        return f"<RenderingImage(id={self.id}, title='{self.title}', rendering_id={self.rendering_id})>"


class RenderingItem(BaseModel):
    """
    Rendering Item model for individual line items in a rendering.

    Each item has:
    - Category (e.g., "Electrical", "Plumbing")
    - Name and specifications
    - Optional image
    - Pricing information
    """

    __tablename__ = "rendering_items"

    # Item details
    category = Column(String(255), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    specifications = Column(JSON, nullable=True)  # Flexible key-value pairs for specs
    notes = Column(Text, nullable=True)

    # Image for this item (optional)
    image_url = Column(String(500), nullable=True)
    material_image_url = Column(String(500), nullable=True)
    product_image_url = Column(String(500), nullable=True)

    # Pricing
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit = Column(String(50), nullable=True)
    unit_price = Column(Numeric(12, 2), nullable=False, default=0)
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    tax = Column(Numeric(12, 2), nullable=True)
    total = Column(Numeric(12, 2), nullable=False, default=0)
    disclaimer = Column(Text, nullable=True)

    # Display settings
    is_material_sample = Column(Boolean, nullable=False, default=False)
    show_in_materials_page = Column(Boolean, nullable=False, default=False)
    show_in_details_page = Column(Boolean, nullable=False, default=True)

    # Ordering
    order_index = Column(Integer, nullable=False, default=0)

    # Optional: Reference to budget item (if imported from budget)
    budget_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("budget_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Foreign key to rendering
    rendering_id = Column(
        UUID(as_uuid=True),
        ForeignKey("renderings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    rendering = relationship("Rendering", back_populates="items")
    budget_item = relationship("BudgetItem", foreign_keys=[budget_item_id])

    def __repr__(self):
        return f"<RenderingItem(id={self.id}, name='{self.name}', rendering_id={self.rendering_id})>"
