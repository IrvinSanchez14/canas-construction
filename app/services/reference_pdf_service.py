"""
PDF Generation Service for Customer References

Draws everything directly on the canvas (no flowables) so each page
is guaranteed to have: branded header + content + footer.

Page layout:
  1) Cover Page — branding, title, placeholder images, prepared by info
  2) References List — all customer references with details
"""

import os
from io import BytesIO
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.models.reference import Reference
from app.core.logging import get_logger

logger = get_logger(__name__)

# Resolve asset paths
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
LOGO_PATH = os.path.join(ASSETS_DIR, 'logo.png')
COVER_IMAGE_PATH = os.path.join(ASSETS_DIR, 'customer_reference_cover.png')
FONT_REGULAR = os.path.join(ASSETS_DIR, 'fonts', 'Figtree-Regular.ttf')
FONT_BOLD = os.path.join(ASSETS_DIR, 'fonts', 'Figtree-Bold.ttf')

# Brand colors
NAVY = colors.HexColor('#1b2850')
SUBTITLE_COLOR = colors.Color(100/255, 110/255, 130/255)
LIGHT_BLUE_BG = colors.Color(210/255, 217/255, 235/255)

# Company info
COMPANY_NAME = "CANA'S  KITCHEN  &  BATH"
COMPANY_ADDRESS = "419 Nashua Street, Milford, NH 03055"
COMPANY_PHONE = "603.554.8223"
COMPANY_WEBSITE = "www.canasconstruction.com"

# Page dimensions
PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 0.75 * inch

# Register fonts
_fonts_registered = False


def _register_fonts():
    global _fonts_registered
    if _fonts_registered:
        return
    try:
        if os.path.exists(FONT_REGULAR):
            pdfmetrics.registerFont(TTFont('Figtree', FONT_REGULAR))
        if os.path.exists(FONT_BOLD):
            pdfmetrics.registerFont(TTFont('Figtree-Bold', FONT_BOLD))
        _fonts_registered = True
    except Exception as e:
        logger.warning(f"Failed to register Figtree fonts: {e}")


def _get_font():
    _register_fonts()
    return 'Figtree' if _fonts_registered else 'Helvetica'


def _get_font_bold():
    _register_fonts()
    return 'Figtree-Bold' if _fonts_registered else 'Helvetica-Bold'


class ReferencePDFService:
    """Generates customer reference PDFs by drawing directly on the canvas."""

    def __init__(self):
        self.font = _get_font()
        self.font_bold = _get_font_bold()

    def _draw_header(self, c: pdfcanvas.Canvas) -> float:
        """Draw branded header. Returns the Y where content area starts."""
        center_x = PAGE_WIDTH / 2
        y = PAGE_HEIGHT - MARGIN

        # Logo
        if os.path.exists(LOGO_PATH):
            logo_w, logo_h = 60, 60
            logo_x = center_x - logo_w / 2
            y -= logo_h
            c.drawImage(LOGO_PATH, logo_x, y, width=logo_w, height=logo_h,
                        preserveAspectRatio=True, mask='auto')
            y -= 6

        # First navy line
        c.setStrokeColor(NAVY)
        c.setLineWidth(2.5)
        c.line(MARGIN, y, PAGE_WIDTH - MARGIN, y)
        y -= 16

        # Company name
        c.setFont(self.font_bold, 13)
        c.setFillColor(NAVY)
        c.drawCentredString(center_x, y, COMPANY_NAME)
        y -= 8

        # Second navy line
        c.setStrokeColor(NAVY)
        c.setLineWidth(2.5)
        c.line(MARGIN, y, PAGE_WIDTH - MARGIN, y)
        y -= 20

        return y

    def _draw_footer(self, c: pdfcanvas.Canvas):
        """Draw company footer at bottom."""
        footer_text = f"{COMPANY_ADDRESS} \u2013 {COMPANY_PHONE} \u2013 {COMPANY_WEBSITE}"
        c.setFont(self.font, 8)
        c.setFillColor(SUBTITLE_COLOR)
        c.drawCentredString(PAGE_WIDTH / 2, 0.5 * inch, footer_text)

    def _draw_cover_page(self, c: pdfcanvas.Canvas):
        """Draw the cover page with branding and placeholder images."""
        content_top = self._draw_header(c)
        center_x = PAGE_WIDTH / 2

        # Calculate image dimensions first so we can center title + image together
        title_font_size = 28
        title_gap = 14  # gap between title and image
        title_h = title_font_size + title_gap

        avail_w = PAGE_WIDTH - 2 * MARGIN
        draw_w = avail_w
        draw_h = 0

        reader = None
        if os.path.exists(COVER_IMAGE_PATH):
            from reportlab.lib.utils import ImageReader
            reader = ImageReader(COVER_IMAGE_PATH)
            orig_w, orig_h = reader.getSize()
            scale = avail_w / orig_w
            draw_w = avail_w
            draw_h = orig_h * scale
            max_h = (content_top - 1.6 * inch) - title_h
            if draw_h > max_h:
                scale = max_h / orig_h
                draw_w = orig_w * scale
                draw_h = max_h

        # Vertically center the title + image block between header and footer band
        total_block_h = title_h + draw_h
        footer_band_top = 0.8 * inch + 60  # band_y + band_h
        available_space = content_top - footer_band_top
        block_top = footer_band_top + (available_space + total_block_h) / 2

        # Title: "Customer Reference." bold
        c.setFont(self.font_bold, title_font_size)
        c.setFillColor(NAVY)
        c.drawCentredString(center_x, block_top - title_font_size, "Customer Reference.")

        # Cover image
        if reader:
            img_y = block_top - title_h - draw_h
            img_x = MARGIN + (avail_w - draw_w) / 2
            c.drawImage(reader, img_x, img_y, width=draw_w, height=draw_h,
                        preserveAspectRatio=True, mask='auto')

        # Footer band: "PREPARED BY" section
        band_h = 60
        band_y = 0.8 * inch
        c.setFillColor(LIGHT_BLUE_BG)
        c.rect(0, band_y, PAGE_WIDTH, band_h, fill=1, stroke=0)

        # Prepared by text
        text_x = MARGIN + 20
        c.setFont(self.font, 9)
        c.setFillColor(NAVY)
        c.drawString(text_x, band_y + band_h - 18, "PREPARED BY:")

        c.setFont(self.font_bold, 12)
        c.drawString(text_x, band_y + band_h - 34, "EDWIN ROSALES")

        c.setFont(self.font, 9)
        c.drawString(text_x, band_y + band_h - 48, "Owner Canas Construction Services LLC")

        self._draw_footer(c)
        c.showPage()

    def _draw_references_page(self, c: pdfcanvas.Canvas, references: List[Reference]):
        """Draw the references list page."""
        content_top = self._draw_header(c)
        center_x = PAGE_WIDTH / 2

        # Title: "CUSTOMERS REFERENCE." bold italic
        y = content_top - 10
        c.setFont(self.font_bold, 20)
        c.setFillColor(NAVY)
        c.drawCentredString(center_x, y, "CUSTOMERS REFERENCE.")
        y -= 35

        # Draw each reference entry
        for ref in references:
            # Check if we need a new page
            if y < 1.2 * inch:
                self._draw_footer(c)
                c.showPage()
                content_top = self._draw_header(c)
                y = content_top - 10

            # Client name (bold, larger font)
            c.setFont(self.font_bold, 12)
            c.setFillColor(NAVY)
            c.drawString(MARGIN, y, ref.client_name)
            y -= 16

            # Location + project description + value + phone
            detail_parts = []
            if ref.location:
                detail_parts.append(ref.location)
            if ref.project_description:
                detail_parts.append(f"({ref.project_description})")
            if ref.project_value:
                detail_parts.append(ref.project_value)
            if ref.phone:
                detail_parts.append(ref.phone)

            detail_line = "  ".join(detail_parts)

            c.setFont(self.font, 11)
            c.setFillColor(colors.black)
            c.drawString(MARGIN, y, detail_line)
            y -= 24

        self._draw_footer(c)
        c.showPage()

    def generate_pdf(self, references: List[Reference]) -> bytes:
        """Generate a customer references PDF.

        Pages:
          1. Cover page with branding
          2. References list

        Args:
            references: List of Reference models

        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        c = pdfcanvas.Canvas(buffer, pagesize=letter)

        # Page 1: Cover page
        self._draw_cover_page(c)

        # Page 2: References list
        self._draw_references_page(c, references)

        c.save()
        buffer.seek(0)
        return buffer.getvalue()


# Singleton instance
reference_pdf_service = ReferencePDFService()


def get_reference_pdf_service() -> ReferencePDFService:
    """Dependency injection for Reference PDF service."""
    return reference_pdf_service
