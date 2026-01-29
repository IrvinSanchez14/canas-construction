"""
PDF Generation Service for Renderings

Generates professional PDF documents for rendering proposals.
"""

from io import BytesIO
from typing import Optional
from decimal import Decimal
import httpx

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from app.models import Rendering
from app.core.logging import get_logger

logger = get_logger(__name__)


class RenderingPDFService:
    """Service for generating rendering PDF documents."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='RenderingTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a1a1a')
        ))
        self.styles.add(ParagraphStyle(
            name='RenderingSubtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#666666')
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#333333')
        ))
        self.styles.add(ParagraphStyle(
            name='ItemName',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#1a1a1a')
        ))

    def _fetch_image(self, url: str, max_width: float, max_height: float) -> Optional[RLImage]:
        """Fetch image from URL and create ReportLab Image object."""
        try:
            response = httpx.get(url, timeout=30, follow_redirects=True)
            response.raise_for_status()

            img_data = BytesIO(response.content)

            # Create image and scale to fit
            img = RLImage(img_data)

            # Calculate scaling to fit within max dimensions while maintaining aspect ratio
            img_width = img.drawWidth
            img_height = img.drawHeight

            width_ratio = max_width / img_width
            height_ratio = max_height / img_height
            scale = min(width_ratio, height_ratio, 1.0)

            img.drawWidth = img_width * scale
            img.drawHeight = img_height * scale

            return img
        except Exception as e:
            logger.warning(f"Failed to fetch image from {url}: {e}")
            return None

    def _build_cover_page(self, rendering: Rendering) -> list:
        """Build cover page elements."""
        elements = []

        elements.append(Spacer(1, 2 * inch))

        # Title
        elements.append(Paragraph(rendering.title, self.styles['RenderingTitle']))

        # Subtitle with project info
        if rendering.visit and rendering.visit.project:
            project_name = rendering.visit.project.name
            elements.append(Paragraph(f"Project: {project_name}", self.styles['RenderingSubtitle']))

        if rendering.description:
            elements.append(Spacer(1, 0.5 * inch))
            elements.append(Paragraph(rendering.description, self.styles['Normal']))

        # Total amount
        if rendering.total_amount:
            elements.append(Spacer(1, 1 * inch))
            total = f"${rendering.total_amount:,.2f}"
            elements.append(Paragraph(f"Total Estimate: {total}", self.styles['RenderingTitle']))

        # Date
        elements.append(Spacer(1, 0.5 * inch))
        if rendering.expiration_date:
            elements.append(Paragraph(
                f"Valid until: {rendering.expiration_date.strftime('%B %d, %Y')}",
                self.styles['RenderingSubtitle']
            ))

        elements.append(PageBreak())
        return elements

    def _build_images_section(self, rendering: Rendering) -> list:
        """Build images section with full-page images."""
        elements = []

        if not rendering.images:
            return elements

        # Sort images by display order
        sorted_images = sorted(rendering.images, key=lambda x: x.display_order)

        for img_record in sorted_images:
            if img_record.is_full_page:
                # Full page image
                img = self._fetch_image(
                    img_record.image_url,
                    max_width=7 * inch,
                    max_height=9 * inch
                )
                if img:
                    elements.append(Spacer(1, 0.5 * inch))
                    if img_record.title:
                        elements.append(Paragraph(img_record.title, self.styles['SectionHeader']))
                    elements.append(img)
                    elements.append(PageBreak())
            else:
                # Regular image (half page)
                img = self._fetch_image(
                    img_record.image_url,
                    max_width=6 * inch,
                    max_height=4 * inch
                )
                if img:
                    if img_record.title:
                        elements.append(Paragraph(img_record.title, self.styles['SectionHeader']))
                    elements.append(img)
                    elements.append(Spacer(1, 0.3 * inch))

        return elements

    def _build_items_table(self, rendering: Rendering) -> list:
        """Build items table section."""
        elements = []

        if not rendering.items:
            return elements

        elements.append(Paragraph("Item Details", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.2 * inch))

        # Sort items by order index
        sorted_items = sorted(rendering.items, key=lambda x: x.order_index)

        # Group by category
        categories = {}
        for item in sorted_items:
            cat = item.category or "General"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        for category, items in categories.items():
            # Category header
            elements.append(Paragraph(category, self.styles['Heading3']))
            elements.append(Spacer(1, 0.1 * inch))

            # Table data
            table_data = [['Description', 'Qty', 'Unit', 'Unit Price', 'Total']]

            for item in items:
                qty = f"{item.quantity:,.2f}" if item.quantity else "-"
                unit = item.unit or "-"
                unit_price = f"${item.unit_price:,.2f}" if item.unit_price else "-"
                total = f"${item.total:,.2f}" if item.total else "-"

                table_data.append([
                    Paragraph(item.name, self.styles['ItemName']),
                    qty,
                    unit,
                    unit_price,
                    total
                ])

            # Create table
            col_widths = [3.5 * inch, 0.7 * inch, 0.7 * inch, 1 * inch, 1 * inch]
            table = Table(table_data, colWidths=col_widths)

            table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333333')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),

                # Body
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 8),

                # Alignment
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),

                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#333333')),
            ]))

            elements.append(table)
            elements.append(Spacer(1, 0.3 * inch))

        return elements

    def _build_total_section(self, rendering: Rendering) -> list:
        """Build total amount section."""
        elements = []

        if rendering.total_amount:
            elements.append(Spacer(1, 0.3 * inch))

            total_data = [
                ['', 'Total:', f"${rendering.total_amount:,.2f}"]
            ]

            total_table = Table(total_data, colWidths=[4.9 * inch, 1 * inch, 1 * inch])
            total_table.setStyle(TableStyle([
                ('FONTNAME', (1, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (1, 0), (-1, 0), 12),
                ('ALIGN', (1, 0), (-1, 0), 'RIGHT'),
                ('LINEABOVE', (1, 0), (-1, 0), 2, colors.HexColor('#333333')),
                ('TOPPADDING', (1, 0), (-1, 0), 10),
            ]))

            elements.append(total_table)

        return elements

    def _build_notes_section(self, rendering: Rendering) -> list:
        """Build notes section if notes exist."""
        elements = []

        if rendering.notes:
            elements.append(Spacer(1, 0.5 * inch))
            elements.append(Paragraph("Notes", self.styles['SectionHeader']))
            elements.append(Paragraph(rendering.notes, self.styles['Normal']))

        return elements

    def generate_pdf(self, rendering: Rendering) -> bytes:
        """
        Generate a PDF document for the rendering.

        Args:
            rendering: Rendering model with images and items loaded

        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )

        elements = []

        # Build document sections
        elements.extend(self._build_cover_page(rendering))
        elements.extend(self._build_images_section(rendering))
        elements.extend(self._build_items_table(rendering))
        elements.extend(self._build_total_section(rendering))
        elements.extend(self._build_notes_section(rendering))

        # Build PDF
        doc.build(elements)

        buffer.seek(0)
        return buffer.getvalue()


# Singleton instance
rendering_pdf_service = RenderingPDFService()


def get_rendering_pdf_service() -> RenderingPDFService:
    """Dependency injection for PDF service."""
    return rendering_pdf_service
