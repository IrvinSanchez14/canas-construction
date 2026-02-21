"""
PDF Generation Service for Renderings

Draws everything directly on the canvas (no flowables) so each page
is guaranteed to have: branded header + content + footer.

Page layout:
  1) 3D Renders (image_type='project') — one full-size image per page
  2) Proposed Materials (image_type='material') — 4 images per page in a 2x2 grid,
     with the material name above each image
  3) Item Details — table with category groups, pricing, and grand total
"""

import os
from io import BytesIO
from typing import Optional, Tuple, List
import httpx

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.models import Rendering
from app.models.rendering import RenderingImage, RenderingItem
from app.core.logging import get_logger

logger = get_logger(__name__)

# Resolve asset paths
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
LOGO_PATH = os.path.join(ASSETS_DIR, 'logo.png')
FONT_REGULAR = os.path.join(ASSETS_DIR, 'fonts', 'Figtree-Regular.ttf')
FONT_BOLD = os.path.join(ASSETS_DIR, 'fonts', 'Figtree-Bold.ttf')

# Brand colors
NAVY = colors.HexColor('#1b2850')
SUBTITLE_COLOR = colors.Color(100/255, 110/255, 130/255)
HEADER_BG = (210/255, 217/255, 235/255)   # table header row
SECTION_BG = (217/255, 225/255, 242/255)   # category section row
BORDER_CLR = (217/255, 217/255, 217/255)   # table grid lines

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


class RenderingPDFService:
    """Generates rendering PDFs by drawing directly on the canvas."""

    def __init__(self):
        self.font = _get_font()
        self.font_bold = _get_font_bold()

    def _fetch_image_reader(self, url: str) -> Optional[Tuple[ImageReader, float, float]]:
        """Fetch image from URL and return ImageReader with original dimensions."""
        try:
            response = httpx.get(url, timeout=30, follow_redirects=True)
            response.raise_for_status()
            img_data = BytesIO(response.content)
            reader = ImageReader(img_data)
            w, h = reader.getSize()
            return reader, float(w), float(h)
        except Exception as e:
            logger.warning(f"Failed to fetch image from {url}: {e}")
            return None

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

    def _draw_3d_render_page(self, c: pdfcanvas.Canvas, img_record: RenderingImage):
        """Draw a single 3D render image filling the page."""
        result = self._fetch_image_reader(img_record.image_url)
        if not result:
            return

        reader, orig_w, orig_h = result
        content_top = self._draw_header(c)
        footer_top = 0.8 * inch

        avail_w = PAGE_WIDTH - 2 * MARGIN
        avail_h = content_top - footer_top

        # Scale to fill available area
        scale = min(avail_w / orig_w, avail_h / orig_h)
        draw_w = orig_w * scale
        draw_h = orig_h * scale

        # Center in available area
        x = MARGIN + (avail_w - draw_w) / 2
        y = footer_top + (avail_h - draw_h) / 2

        c.drawImage(reader, x, y, width=draw_w, height=draw_h,
                    preserveAspectRatio=True)

        self._draw_footer(c)
        c.showPage()

    def _draw_materials_pages(self, c: pdfcanvas.Canvas, materials: List[RenderingImage]):
        """Draw material images in a 2x2 grid (4 per page) with title above each."""
        if not materials:
            return

        # Grid layout: 2 columns x 2 rows per page
        cols = 2
        rows = 2
        per_page = cols * rows
        gap = 0.3 * inch
        title_height = 16  # space for the material name text

        for page_start in range(0, len(materials), per_page):
            page_materials = materials[page_start:page_start + per_page]

            content_top = self._draw_header(c)
            footer_top = 0.8 * inch

            avail_w = PAGE_WIDTH - 2 * MARGIN
            avail_h = content_top - footer_top

            # Cell dimensions
            cell_w = (avail_w - gap) / cols
            cell_h = (avail_h - gap) / rows
            img_max_h = cell_h - title_height - 8  # leave room for title + padding

            for idx, img_record in enumerate(page_materials):
                col = idx % cols
                row = idx // cols

                # Cell top-left corner
                cell_x = MARGIN + col * (cell_w + gap)
                cell_y_top = content_top - row * (cell_h + gap)

                # Draw material name above the image
                title = img_record.title or "Material"
                c.setFont(self.font_bold, 10)
                c.setFillColor(NAVY)
                c.drawString(cell_x, cell_y_top - title_height + 2, title)

                # Fetch and draw image below the title
                result = self._fetch_image_reader(img_record.image_url)
                if not result:
                    continue

                reader, orig_w, orig_h = result

                img_area_top = cell_y_top - title_height - 4
                img_area_w = cell_w
                img_area_h = img_max_h

                # Scale to fit cell
                scale = min(img_area_w / orig_w, img_area_h / orig_h)
                draw_w = orig_w * scale
                draw_h = orig_h * scale

                # Center image in cell area
                img_x = cell_x + (img_area_w - draw_w) / 2
                img_y = img_area_top - draw_h

                c.drawImage(reader, img_x, img_y, width=draw_w, height=draw_h,
                            preserveAspectRatio=True)

            self._draw_footer(c)
            c.showPage()

    def _draw_item_detail_page(self, c: pdfcanvas.Canvas, item: RenderingItem,
                               job_name: str, expiration_date: str):
        """Draw one item per page: specs table on left, product image on right.

        Layout matches the example:
        - Navy header row: "Job:" + project address
        - Category name centered bold
        - Specifications rows (key: value from JSON)
        - Subtotal row (blue bg, bold)
        - Delivery Fee / Tax rows
        - Total row (blue bg, bold)
        - Disclaimer text
        - "Labor not included" centered bold
        - Expiration date row
        - Product image on the right side
        """
        content_top = self._draw_header(c)

        # Layout: left table ~48%, gap, right image ~48%
        avail_w = PAGE_WIDTH - 2 * MARGIN
        table_w = avail_w * 0.48
        img_area_w = avail_w * 0.48
        gap = avail_w * 0.04
        table_x = MARGIN
        img_x = MARGIN + table_w + gap

        row_h = 18
        label_w = table_w * 0.48
        value_w = table_w * 0.52

        y = content_top

        def _row_rect(rx, ry, rw, rh, bg=None):
            """Draw a table cell rectangle."""
            if bg:
                c.setFillColorRGB(*bg)
                c.rect(rx, ry, rw, rh, fill=1, stroke=0)
            c.setStrokeColorRGB(*BORDER_CLR)
            c.setLineWidth(0.5)
            c.rect(rx, ry, rw, rh, fill=0, stroke=1)

        def _draw_full_row(text_left, text_right, bg=None, bold=False):
            """Draw a full-width row with two columns."""
            nonlocal y
            ry = y - row_h
            _row_rect(table_x, ry, label_w, row_h, bg)
            _row_rect(table_x + label_w, ry, value_w, row_h, bg)
            font = self.font_bold if bold else self.font
            c.setFont(font, 9)
            c.setFillColor(colors.black)
            c.drawString(table_x + 4, ry + 5, text_left)
            c.drawString(table_x + label_w + 4, ry + 5, text_right)
            y = ry

        def _draw_full_span_row(text, bg=None, bold=False, centered=False):
            """Draw a single cell spanning full table width."""
            nonlocal y
            ry = y - row_h
            _row_rect(table_x, ry, table_w, row_h, bg)
            font = self.font_bold if bold else self.font
            c.setFont(font, 9)
            c.setFillColor(colors.black if not bg else colors.white if bg == NAVY_RGB else colors.black)
            if centered:
                c.drawCentredString(table_x + table_w / 2, ry + 5, text)
            else:
                c.drawString(table_x + 4, ry + 5, text)
            y = ry

        def _draw_price_row(label, amount, bg=None, bold=False):
            """Draw a price row: label left, $amount right-aligned."""
            nonlocal y
            ry = y - row_h
            _row_rect(table_x, ry, label_w, row_h, bg)
            _row_rect(table_x + label_w, ry, value_w, row_h, bg)
            font = self.font_bold if bold else self.font
            c.setFont(font, 9)
            c.setFillColor(colors.black)
            c.drawString(table_x + 4, ry + 5, label)
            c.drawRightString(table_x + table_w - 4, ry + 5, amount)
            y = ry

        NAVY_RGB = (27/255, 40/255, 80/255)

        # --- Job header row (navy background, white text) ---
        job_y = y - row_h
        _row_rect(table_x, job_y, table_w, row_h, NAVY_RGB)
        c.setFont(self.font_bold, 10)
        c.setFillColor(colors.white)
        c.drawString(table_x + 4, job_y + 5, "Job:")
        c.drawString(table_x + label_w + 4, job_y + 5, job_name)
        y = job_y

        # Empty separator
        y -= 4

        # --- Category name centered ---
        category = item.category or "General"
        _draw_full_span_row(category, bold=True, centered=True)

        # --- Specifications from JSON ---
        specs = item.specifications or {}
        if isinstance(specs, dict):
            for key, value in specs.items():
                _draw_full_row(f"{key}:", str(value))

        # Empty separator
        y -= 4

        # --- Quantity row ---
        qty_str = f"{item.quantity}" if item.quantity else "1"
        if item.unit:
            qty_str = f"{qty_str}{item.unit}"
        _draw_full_row("Quantity:", qty_str)

        # Empty separator
        y -= 4

        # --- Subtotal row (blue bg, bold) ---
        subtotal = float(item.subtotal or 0)
        _draw_price_row("Subtotal:", f"${subtotal:,.2f}", bg=HEADER_BG, bold=True)

        # --- Delivery Fee ---
        _draw_price_row("Delivery Fee:", "$0.00")

        # --- Tax row ---
        tax = float(item.tax or 0)
        _draw_price_row("MA Sales Tax:", f"${tax:,.2f}")

        # --- Total row (blue bg, bold) ---
        total = float(item.total or 0)
        _draw_price_row("Total:", f"${total:,.2f}", bg=HEADER_BG, bold=True)

        # --- Disclaimer text ---
        disclaimer = item.disclaimer or (
            "Pricing is strictly an estimate - the final pricing will "
            "be determined once the on-site measurement, final "
            "layout, and product selection are signed off on."
        )
        # Draw disclaimer in a wrapped box
        disclaimer_y = y - 4
        c.setFont(self.font, 7)
        c.setFillColor(colors.black)
        # Simple word-wrap
        words = disclaimer.split()
        lines = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            if c.stringWidth(test, self.font, 7) < table_w - 12:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        box_h = max(len(lines) * 10 + 6, row_h)
        box_y = disclaimer_y - box_h
        _row_rect(table_x, box_y, table_w, box_h)
        text_y = disclaimer_y - 10
        for line in lines:
            c.drawCentredString(table_x + table_w / 2, text_y, line)
            text_y -= 10
        y = box_y

        # --- "Labor not included" centered bold ---
        _draw_full_span_row("Labor not included", bold=True, centered=True)

        # --- Expiration date ---
        if expiration_date:
            exp_y = y - row_h
            _row_rect(table_x, exp_y, table_w, row_h)
            c.setFont(self.font, 9)
            c.setFillColor(colors.black)
            c.drawString(table_x + 4, exp_y + 5, f"This estimate expires on:       {expiration_date}")
            y = exp_y

        # --- Product image on the right side ---
        img_url = item.product_image_url or item.image_url
        if img_url:
            result = self._fetch_image_reader(img_url)
            if result:
                reader, orig_w, orig_h = result
                # Available height from content_top down to footer
                img_avail_h = content_top - 0.8 * inch
                scale = min(img_area_w / orig_w, img_avail_h / orig_h)
                draw_w = orig_w * scale
                draw_h = orig_h * scale
                # Top-align with content, center horizontally in right area
                img_draw_x = img_x + (img_area_w - draw_w) / 2
                img_draw_y = content_top - draw_h
                c.drawImage(reader, img_draw_x, img_draw_y,
                            width=draw_w, height=draw_h,
                            preserveAspectRatio=True)

        self._draw_footer(c)
        c.showPage()

    def _draw_items_pages(self, c: pdfcanvas.Canvas, rendering: Rendering):
        """Draw item detail pages — one item per page with specs table + image."""
        items = [item for item in (rendering.items or []) if item.show_in_details_page]
        if not items:
            return

        sorted_items = sorted(items, key=lambda x: x.order_index)

        # Get job name from project
        job_name = ""
        if rendering.visit and rendering.visit.project:
            job_name = rendering.visit.project.name or ""
            if hasattr(rendering.visit.project, 'address') and rendering.visit.project.address:
                job_name = rendering.visit.project.address

        # Expiration date
        expiration_date = ""
        if rendering.expiration_date:
            try:
                from datetime import datetime
                if isinstance(rendering.expiration_date, str):
                    dt = datetime.fromisoformat(rendering.expiration_date)
                else:
                    dt = rendering.expiration_date
                expiration_date = dt.strftime("%B %d, %Y")
            except Exception:
                expiration_date = str(rendering.expiration_date)

        for item in sorted_items:
            self._draw_item_detail_page(c, item, job_name, expiration_date)

    def generate_pdf(self, rendering: Rendering) -> bytes:
        """Generate a rendering PDF.

        Order:
          1. 3D Renders (image_type='project') — one per page, full size
          2. Proposed Materials (image_type='material') — 4 per page, 2x2 grid with titles
          3. Item Details — table grouped by category with pricing and grand total

        Args:
            rendering: Rendering model with images loaded

        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        c = pdfcanvas.Canvas(buffer, pagesize=letter)

        if not rendering.images:
            self._draw_header(c)
            self._draw_footer(c)
            c.showPage()
        else:
            sorted_images = sorted(rendering.images, key=lambda x: x.display_order)

            # Split by type
            renders_3d = [img for img in sorted_images if img.image_type == 'project']
            materials = [img for img in sorted_images if img.image_type == 'material']

            # Section 1: 3D renders — one per page
            for img_record in renders_3d:
                self._draw_3d_render_page(c, img_record)

            # Section 2: Materials — 4 per page grid with titles
            self._draw_materials_pages(c, materials)

            # Section 3: Item Details — one item per page with specs + image
            self._draw_items_pages(c, rendering)

            detail_items = [i for i in (rendering.items or []) if i.show_in_details_page]
            # If nothing was drawn at all, show empty page
            if not renders_3d and not materials and not detail_items:
                self._draw_header(c)
                self._draw_footer(c)
                c.showPage()

        c.save()
        buffer.seek(0)
        return buffer.getvalue()


# Singleton instance
rendering_pdf_service = RenderingPDFService()


def get_rendering_pdf_service() -> RenderingPDFService:
    """Dependency injection for PDF service."""
    return rendering_pdf_service
