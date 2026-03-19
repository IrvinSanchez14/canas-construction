"""
PDF Generation Service for Change Orders

Matches the reference PDF layout exactly:
  - Top-left: "CHANGE ORDER" title (bold, underlined) + date (underlined)
  - Top-right: Company logo
  - Company name + address
  - TO: client / Address: / Job Name:
  - Observations with ➢ bullets
  - Items table with light blue header
  - Total row
  - Signature boxes (contractor + customer)
  - Footer note + "Thanks for your business."
"""

import os
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from decimal import Decimal

from app.models.change_order import ChangeOrder
from app.core.logging import get_logger

# Profit model: cost is 65% of selling price, profit is 35%
COST_RATIO = Decimal('0.65')

logger = get_logger(__name__)

# Assets
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
LOGO_PATH = os.path.join(ASSETS_DIR, 'logo.png')
FONT_REGULAR = os.path.join(ASSETS_DIR, 'fonts', 'Figtree-Regular.ttf')
FONT_BOLD = os.path.join(ASSETS_DIR, 'fonts', 'Figtree-Bold.ttf')

# Colors
HEADER_BG = (210/255, 217/255, 235/255)
BORDER_CLR = (180/255, 180/255, 180/255)

# Company
COMPANY_NAME = "Canas Construction Services LLC"
COMPANY_ADDRESS = "419 Nashua Street, Milford, NH 03055"

# Page
PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch

_fonts_ok = False


def _register_fonts():
    global _fonts_ok
    if _fonts_ok:
        return
    try:
        if os.path.exists(FONT_REGULAR):
            pdfmetrics.registerFont(TTFont('Figtree', FONT_REGULAR))
        if os.path.exists(FONT_BOLD):
            pdfmetrics.registerFont(TTFont('Figtree-Bold', FONT_BOLD))
        _fonts_ok = True
    except Exception as e:
        logger.warning(f"Font registration failed: {e}")


def _font():
    _register_fonts()
    return 'Figtree' if _fonts_ok else 'Helvetica'


def _font_bold():
    _register_fonts()
    return 'Figtree-Bold' if _fonts_ok else 'Helvetica-Bold'


def _currency(amount) -> str:
    try:
        return f"${float(amount):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _wrap(text: str, font_name: str, font_size: float, max_w: float, c) -> list:
    """Word-wrap text into lines that fit max_w."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if c.stringWidth(test, font_name, font_size) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


class ChangeOrderPDFService:
    """Generates Change Order PDFs matching the reference design."""

    def __init__(self):
        self.font = _font()
        self.font_bold = _font_bold()

    def generate_pdf(self, change_order: ChangeOrder) -> bytes:
        buffer = BytesIO()
        c = pdfcanvas.Canvas(buffer, pagesize=letter)

        # --- Context ---
        project = change_order.project
        client = project.client if project else None
        client_name = client.name if client else ""
        project_address = project.address if project else ""
        project_name = project.name if project else ""
        co_date = change_order.created_at.strftime("%m/%d/%y") if change_order.created_at else ""

        # ============================================================
        # HEADER SECTION  (top of page)
        # ============================================================
        y = PAGE_H - MARGIN

        # Logo — top-right
        logo_w, logo_h = 90, 90
        if os.path.exists(LOGO_PATH):
            c.drawImage(
                LOGO_PATH,
                PAGE_W - MARGIN - logo_w, y - logo_h,
                width=logo_w, height=logo_h,
                preserveAspectRatio=True, mask='auto',
            )

        # "CHANGE ORDER" — top-left, bold 24pt, underlined
        c.setFont(self.font_bold, 24)
        c.setFillColor(colors.black)
        c.drawString(MARGIN, y - 18, "CHANGE ORDER")
        title_w = c.stringWidth("CHANGE ORDER", self.font_bold, 24)
        c.setStrokeColor(colors.black)
        c.setLineWidth(1.5)
        c.line(MARGIN, y - 22, MARGIN + title_w, y - 22)

        # Date — below title, bold 12pt, underlined
        y -= 40
        c.setFont(self.font_bold, 12)
        c.drawString(MARGIN, y, co_date)
        date_w = c.stringWidth(co_date, self.font_bold, 12)
        c.setLineWidth(1)
        c.line(MARGIN, y - 3, MARGIN + date_w, y - 3)

        # Company name + address — smaller, regular
        y -= 22
        c.setFont(self.font, 10)
        c.drawString(MARGIN, y, COMPANY_NAME)
        y -= 14
        c.drawString(MARGIN, y, COMPANY_ADDRESS)

        # ============================================================
        # CLIENT / JOB INFO
        # ============================================================
        y -= 30

        c.setFont(self.font_bold, 11)
        c.drawString(MARGIN, y, f"TO: {client_name}.")
        y -= 20

        c.setFont(self.font_bold, 11)
        c.drawString(MARGIN, y, f"Address: {project_address}")
        y -= 28

        c.setFont(self.font_bold, 11)
        c.drawString(MARGIN, y, f"Job Name: {project_name}.")

        # ============================================================
        # OBSERVATIONS
        # ============================================================
        y -= 22
        observations = change_order.observations or []
        if observations:
            c.setFont(self.font_bold, 11)
            c.drawString(MARGIN, y, "Observations:")
            y -= 18

            c.setFont(self.font, 9.5)
            bullet_indent = MARGIN + 20
            text_indent = MARGIN + 36
            text_max_w = PAGE_W - MARGIN - text_indent - 10

            for obs in observations:
                # ➢ bullet
                c.setFont(self.font, 10)
                c.drawString(bullet_indent, y, "\u27A2")
                c.setFont(self.font, 9.5)

                lines = _wrap(obs, self.font, 9.5, text_max_w, c)
                for line in lines:
                    c.drawString(text_indent, y, line)
                    y -= 13
                y -= 2  # small gap between bullets

        # ============================================================
        # ITEMS TABLE
        # ============================================================
        y -= 14

        table_w = PAGE_W - 2 * MARGIN
        # Column widths matching the reference proportions
        cw = {
            'num':   table_w * 0.050,   # row #
            'code':  table_w * 0.085,   # ITEM#
            'desc':  table_w * 0.365,   # Description
            'unit':  table_w * 0.100,   # UNIT
            'qty':   table_w * 0.100,   # Quantity
            'price': table_w * 0.150,   # Unit price
            'sub':   table_w * 0.150,   # Subtotal
        }
        col_order = ['num', 'code', 'desc', 'unit', 'qty', 'price', 'sub']
        hdr_row_h = 22

        def _col_x(col_name):
            """Return left-x for a column."""
            x = MARGIN
            for k in col_order:
                if k == col_name:
                    return x
                x += cw[k]
            return x

        def _draw_cell_borders(ry, rh):
            """Draw outer rect + vertical column dividers for one row."""
            c.setStrokeColorRGB(*BORDER_CLR)
            c.setLineWidth(0.5)
            c.rect(MARGIN, ry, table_w, rh, fill=0, stroke=1)
            x = MARGIN
            for k in col_order[:-1]:  # skip last (right border already drawn)
                x += cw[k]
                c.line(x, ry, x, ry + rh)

        # --- Header row (light-blue background) ---
        hdr_y = y - hdr_row_h
        c.setFillColorRGB(*HEADER_BG)
        c.rect(MARGIN, hdr_y, table_w, hdr_row_h, fill=1, stroke=0)
        _draw_cell_borders(hdr_y, hdr_row_h)

        c.setFont(self.font_bold, 9)
        c.setFillColor(colors.black)
        text_baseline = hdr_y + 7
        c.drawString(_col_x('num') + 4,   text_baseline, ".")
        c.drawString(_col_x('code') + 4,  text_baseline, "ITEM#")
        c.drawString(_col_x('desc') + 4,  text_baseline, "Description")
        c.drawString(_col_x('unit') + 4,  text_baseline, "UNIT")
        c.drawString(_col_x('qty') + 4,   text_baseline, "Quantity")
        c.drawString(_col_x('price') + 4, text_baseline, "Unit price")
        c.drawString(_col_x('sub') + 4,   text_baseline, "Subtotal")

        y = hdr_y

        # --- Item rows ---
        grand_total = 0.0
        items = sorted(change_order.change_order_items, key=lambda x: x.order_index)

        for idx, item in enumerate(items, 1):
            # Word-wrap description
            desc_max = cw['desc'] - 10
            desc_lines = _wrap(item.description, self.font, 9, desc_max, c)
            row_h = max(hdr_row_h, len(desc_lines) * 13 + 9)

            # Page break check
            if y - row_h < MARGIN + 140:
                c.showPage()
                y = PAGE_H - MARGIN

            item_y = y - row_h
            _draw_cell_borders(item_y, row_h)

            c.setFont(self.font, 9)
            c.setFillColor(colors.black)

            # Text baseline — vertically centered for single-line cells
            mid_baseline = item_y + (row_h / 2) - 4
            # Description starts from top
            desc_baseline = item_y + row_h - 14

            # Row #
            c.drawCentredString(_col_x('num') + cw['num'] / 2, mid_baseline, str(idx))

            # Item code
            c.drawString(_col_x('code') + 6, mid_baseline, item.item_code or '')

            # Description (multi-line, top-aligned)
            for i, line in enumerate(desc_lines):
                c.drawString(_col_x('desc') + 6, desc_baseline - i * 13, line)

            # Unit — centered vertically
            c.drawString(_col_x('unit') + 6, mid_baseline, item.unit or '')

            # Quantity — centered
            c.drawCentredString(_col_x('qty') + cw['qty'] / 2, mid_baseline, str(item.quantity))

            # Unit price — show selling price (real price / 0.65)
            real_price = float(item.unit_price or 0)
            selling_price = real_price / float(COST_RATIO) if real_price > 0 else 0
            qty = float(item.quantity or 0)
            line_subtotal = qty * selling_price

            c.drawRightString(_col_x('price') + cw['price'] - 6, mid_baseline, _currency(selling_price))

            # Subtotal — quantity * selling price
            c.drawRightString(_col_x('sub') + cw['sub'] - 6, mid_baseline, _currency(line_subtotal))

            grand_total += line_subtotal
            y = item_y

        # --- Total row (only last two columns) ---
        total_row_h = hdr_row_h
        total_y = y - total_row_h
        total_x = _col_x('price')
        total_w = cw['price'] + cw['sub']

        c.setStrokeColorRGB(*BORDER_CLR)
        c.setLineWidth(0.5)
        c.rect(total_x, total_y, total_w, total_row_h, fill=0, stroke=1)
        c.line(total_x + cw['price'], total_y, total_x + cw['price'], total_y + total_row_h)

        c.setFont(self.font_bold, 10)
        c.setFillColor(colors.black)
        c.drawRightString(total_x + cw['price'] - 6, total_y + 6, "Total")
        c.drawRightString(total_x + total_w - 6, total_y + 6, _currency(grand_total))

        y = total_y

        # ============================================================
        # SIGNATURE SECTION
        # ============================================================
        y -= 30

        # Page break check
        if y - 60 < MARGIN + 60:
            c.showPage()
            y = PAGE_H - MARGIN - 40

        sig_w = (table_w - 16) / 2
        sig_h = 50

        c.setStrokeColorRGB(*BORDER_CLR)
        c.setLineWidth(0.5)

        # Left box — Contractor
        left_y = y - sig_h
        c.rect(MARGIN, left_y, sig_w, sig_h, fill=0, stroke=1)
        c.setFont(self.font_bold, 8)
        c.setFillColor(colors.black)
        c.drawString(MARGIN + 6, left_y + sig_h - 14, "DATE:")
        c.drawString(MARGIN + 6, left_y + 8, "AUTHORIZED SIGNATURE CONTRACTOR:")

        # Right box — Customer
        right_x = MARGIN + sig_w + 16
        c.rect(right_x, left_y, sig_w, sig_h, fill=0, stroke=1)
        c.drawString(right_x + 6, left_y + sig_h - 14, "DATE:")
        c.drawString(right_x + 6, left_y + 8, "AUTHORIZED SIGNATURE (CUSTOMER)")

        y = left_y

        # ============================================================
        # FOOTER NOTE
        # ============================================================
        y -= 28

        note = (
            "NOTE: THIS CHANGE ORDER WILL BE ATTACHED TO ORIGINAL CONTRACT, "
            "AND CUSTOMER NEED TO PAY THIS CHANGE ORDER WHEN WE DONE THIS EXTRA WORK"
        )
        c.setFont(self.font_bold, 7.5)
        c.setFillColor(colors.black)
        note_lines = _wrap(note, self.font_bold, 7.5, PAGE_W - 2 * MARGIN, c)
        for line in note_lines:
            c.drawString(MARGIN, y, line)
            y -= 11

        y -= 6
        c.setFont(self.font, 9)
        c.drawString(MARGIN, y, "Thanks for your business.")

        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer.getvalue()


# Singleton
change_order_pdf_service = ChangeOrderPDFService()


def get_change_order_pdf_service() -> ChangeOrderPDFService:
    """Dependency injection for Change Order PDF service."""
    return change_order_pdf_service
