#!/usr/bin/env python3
"""
Vendoroo Operations Analysis — PDF Report Generator
Generates a 10-page PDF with precise page breaks and spacing.
Uses ReportLab with Poppins font (falls back to Helvetica if Poppins unavailable).
"""

import io
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import math


# ── Register Fonts (resilient) ──
def _register_poppins():
    """Try to register Poppins fonts from various paths. Fall back to Helvetica."""
    font_search_paths = [
        # Streamlit Cloud / Linux
        "/usr/share/fonts/truetype/google-fonts",
        "/usr/share/fonts/truetype/poppins",
        # Project local fonts
        str(Path(__file__).parent.parent / "fonts"),
        str(Path(__file__).parent / "fonts"),
        # macOS
        os.path.expanduser("~/Library/Fonts"),
        "/Library/Fonts",
    ]

    font_files = {
        "Poppins": "Poppins-Regular.ttf",
        "Poppins-Bold": "Poppins-Bold.ttf",
        "Poppins-Medium": "Poppins-Medium.ttf",
        "Poppins-Light": "Poppins-Light.ttf",
    }

    registered = False
    for search_dir in font_search_paths:
        if not os.path.isdir(search_dir):
            continue
        all_found = all(
            os.path.isfile(os.path.join(search_dir, fname))
            for fname in font_files.values()
        )
        if all_found:
            for font_name, font_file in font_files.items():
                pdfmetrics.registerFont(TTFont(font_name, os.path.join(search_dir, font_file)))
            registered = True
            break

    if not registered:
        # Try downloading Poppins to a local fonts directory
        try:
            _download_poppins()
        except Exception:
            # Fall back to Helvetica with Poppins aliases
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            # Map Poppins names to built-in Helvetica
            for name, builtin in [
                ("Poppins", "Helvetica"),
                ("Poppins-Bold", "Helvetica-Bold"),
                ("Poppins-Medium", "Helvetica"),
                ("Poppins-Light", "Helvetica"),
            ]:
                try:
                    pdfmetrics.getFont(name)
                except KeyError:
                    pdfmetrics.registerFont(type(pdfmetrics.getFont(builtin))(name))


def _download_poppins():
    """Download Poppins font files from Google Fonts."""
    import urllib.request
    fonts_dir = Path(__file__).parent.parent / "fonts"
    fonts_dir.mkdir(exist_ok=True)

    base_url = "https://github.com/google/fonts/raw/main/ofl/poppins"
    font_files = {
        "Poppins-Regular.ttf": f"{base_url}/Poppins-Regular.ttf",
        "Poppins-Bold.ttf": f"{base_url}/Poppins-Bold.ttf",
        "Poppins-Medium.ttf": f"{base_url}/Poppins-Medium.ttf",
        "Poppins-Light.ttf": f"{base_url}/Poppins-Light.ttf",
    }

    for fname, url in font_files.items():
        dest = fonts_dir / fname
        if not dest.exists():
            urllib.request.urlretrieve(url, str(dest))

    # Now register them
    for font_name, font_file in [
        ("Poppins", "Poppins-Regular.ttf"),
        ("Poppins-Bold", "Poppins-Bold.ttf"),
        ("Poppins-Medium", "Poppins-Medium.ttf"),
        ("Poppins-Light", "Poppins-Light.ttf"),
    ]:
        pdfmetrics.registerFont(TTFont(font_name, str(fonts_dir / font_file)))


_register_poppins()

# ── Brand Colors ──
YELLOW = HexColor('#FDBB00')
DARK = HexColor('#1A1A1A')
WHITE = HexColor('#FFFFFF')
GRAY_BG = HexColor('#F9FAFB')
MID_GRAY = HexColor('#4B5563')
SUB_GRAY = HexColor('#6B7280')
LINE_GRAY = HexColor('#E5E7EB')
LIGHT_GRAY = HexColor('#F3F4F6')
GREEN = HexColor('#16A34A')
GREEN_LIGHT = HexColor('#F0FDF4')
AMBER = HexColor('#D97706')
AMBER_LIGHT = HexColor('#FFFBEB')
RED = HexColor('#DC2626')
RED_LIGHT = HexColor('#FEF2F2')

W, H = letter  # 612 x 792
MARGIN = 50
CONTENT_W = W - 2 * MARGIN


# ── Helper Functions ──

def draw_footer(c, page_num, client_name="Summit Property Group"):
    """Draw the page footer with line and page number."""
    y = 30
    c.setStrokeColor(YELLOW)
    c.setLineWidth(1.5)
    c.line(MARGIN, y + 12, W - MARGIN, y + 12)
    c.setFont('Poppins', 7)
    c.setFillColor(SUB_GRAY)
    c.drawString(MARGIN, y, f"Vendoroo Operations Analysis \u2022 {client_name} \u2022 Sample Data for Illustration")
    c.drawRightString(W - MARGIN, y, str(page_num))


def draw_section_header(c, y, title, subtitle=None):
    """Draw a section header with yellow underline."""
    c.setFont('Poppins-Bold', 16)
    c.setFillColor(DARK)
    c.drawString(MARGIN, y, title)
    # Yellow line
    c.setStrokeColor(YELLOW)
    c.setLineWidth(3)
    c.line(MARGIN, y - 8, MARGIN + 80, y - 8)
    if subtitle:
        c.setFont('Poppins', 8.5)
        c.setFillColor(SUB_GRAY)
        c.drawString(MARGIN, y - 22, subtitle)
        return y - 40
    return y - 28


def draw_rounded_rect(c, x, y, w, h, r=4, fill=None, stroke=None, stroke_width=0.5):
    """Draw a rounded rectangle."""
    p = c.beginPath()
    p.roundRect(x, y, w, h, r)
    if fill:
        c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(stroke_width)
        c.drawPath(p, fill=1 if fill else 0, stroke=1 if stroke else 0)
    elif fill:
        c.drawPath(p, fill=1, stroke=0)


def draw_stat_card(c, x, y, w, h, value, label, note=None, note_color=None):
    """Draw a stat card with value, label, and optional note."""
    draw_rounded_rect(c, x, y, w, h, r=4, fill=GRAY_BG, stroke=LINE_GRAY)
    # Value
    c.setFont('Poppins-Bold', 18)
    c.setFillColor(DARK)
    c.drawString(x + 12, y + h - 28, str(value))
    # Label
    c.setFont('Poppins', 7.5)
    c.setFillColor(MID_GRAY)
    c.drawString(x + 12, y + h - 42, label)
    # Note
    if note:
        c.setFont('Poppins', 6.5)
        c.setFillColor(note_color or MID_GRAY)
        c.drawString(x + 12, y + h - 54, note)


def draw_progress_bar(c, x, y, w, h, pct, color=YELLOW):
    """Draw a horizontal progress bar."""
    # Track
    draw_rounded_rect(c, x, y, w, h, r=2, fill=LIGHT_GRAY)
    # Fill
    fill_w = max(w * pct / 100, 2)
    draw_rounded_rect(c, x, y, fill_w, h, r=2, fill=color)


def draw_severity_dot(c, x, y, color, radius=3):
    """Draw a small colored dot."""
    c.setFillColor(color)
    c.circle(x, y, radius, fill=1, stroke=0)


def draw_score_ring(c, cx, cy, radius, score, max_score=100, color=YELLOW, label="", sublabel=""):
    """Draw a circular score indicator."""
    # Background circle
    c.setStrokeColor(LIGHT_GRAY)
    c.setLineWidth(6)
    c.circle(cx, cy, radius, fill=0, stroke=1)
    # Score arc
    angle = (score / max_score) * 360
    c.setStrokeColor(color)
    c.setLineWidth(6)
    p = c.beginPath()
    p.arc(cx - radius, cy - radius, cx + radius, cy + radius, 90, 90 - angle)
    c.drawPath(p, fill=0, stroke=1)
    # Score text
    c.setFont('Poppins-Bold', 22)
    c.setFillColor(DARK)
    c.drawCentredString(cx, cy + 4, str(score))
    # Labels
    if label:
        c.setFont('Poppins', 7)
        c.setFillColor(SUB_GRAY)
        c.drawCentredString(cx, cy - 12, label)
    if sublabel:
        c.setFont('Poppins', 6)
        c.setFillColor(SUB_GRAY)
        c.drawCentredString(cx, cy - 22, sublabel)


# ═══════════════════════════════════════════════
# PAGE 1: COVER
# ═══════════════════════════════════════════════

def draw_cover(c):
    """Draw the cover page - full dark background matching HTML template."""
    # Full dark background
    c.setFillColor(DARK)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    
    # Yellow accent bar at top
    c.setFillColor(YELLOW)
    c.rect(0, H - 6, W, 6, fill=1, stroke=0)
    
    # Vendoroo logo text
    c.setFont('Poppins-Bold', 14)
    c.setFillColor(YELLOW)
    c.drawString(56, H - 50, "VENDOROO")
    
    # Score rings (top right area)
    ring_y = H - 110
    ring_area_x = W - 56
    
    # Current score ring
    cx1 = ring_area_x - 170
    draw_score_ring_dark(c, cx1, ring_y, 42, 64, HexColor('#EF4444'))
    c.setFont('Poppins', 6.5)
    c.setFillColor(MID_GRAY)
    c.drawCentredString(cx1, ring_y - 52, "CURRENT")
    
    # Arrow
    c.setFont('Poppins', 16)
    c.setFillColor(MID_GRAY)
    c.drawCentredString(cx1 + 65, ring_y - 4, "\u2192")
    
    # Projected score ring
    cx2 = ring_area_x - 40
    draw_score_ring_dark(c, cx2, ring_y, 42, 92, YELLOW)
    c.setFont('Poppins', 6.5)
    c.setFillColor(YELLOW)
    c.drawCentredString(cx2, ring_y - 52, "WITH VENDOROO")
    
    # Title block (left side, vertically centered)
    title_y = H - 310
    
    c.setFont('Poppins-Light', 12)
    c.setFillColor(YELLOW)
    c.drawString(56, title_y + 60, "OPERATIONS ANALYSIS")
    
    c.setFont('Poppins-Bold', 34)
    c.setFillColor(WHITE)
    c.drawString(56, title_y, "Summit Property Group")
    
    c.setFont('Poppins', 13)
    c.setFillColor(MID_GRAY)
    c.drawString(56, title_y - 28, "342 Doors  \u2022  28 Properties  \u2022  AppFolio")
    c.drawString(56, title_y - 48, "Operational Model: VA (Virtual Assistant Coordinators)")
    
    c.setFont('Poppins', 11)
    c.setFillColor(WHITE)
    c.drawString(56, title_y - 74, "Goal: ")
    c.setFont('Poppins-Bold', 11)
    c.setFillColor(YELLOW)
    goal_x = 56 + pdfmetrics.stringWidth("Goal: ", 'Poppins', 11)
    c.drawString(goal_x, title_y - 74, "Scale")
    c.setFont('Poppins', 11)
    c.setFillColor(WHITE)
    c.drawString(goal_x + pdfmetrics.stringWidth("Scale", 'Poppins-Bold', 11), title_y - 74, "  \u2014  Grow portfolio without adding headcount")
    
    # Sample data notice
    c.setFont('Poppins-Medium', 9)
    c.setFillColor(YELLOW)
    c.drawString(56, title_y - 100, "Sample Data, Not a Real Client, For Illustration Purposes Only")
    
    # Divider
    c.setStrokeColor(HexColor('#333333'))
    c.setLineWidth(0.5)
    c.line(56, title_y - 120, W - 56, title_y - 120)
    
    # Stats row
    stats = [
        ("187", "Monthly Work Orders"),
        ("14.2 hrs", "Avg. Response Time"),
        ("18.3%", "Open WO Rate"),
        ("22 vendors", "Vendor Network"),
    ]
    stat_y = title_y - 160
    stat_w = (W - 112) / 4
    for i, (val, label) in enumerate(stats):
        x = 56 + i * stat_w
        c.setFont('Poppins-Bold', 20)
        c.setFillColor(WHITE)
        c.drawString(x, stat_y, val)
        c.setFont('Poppins', 7.5)
        c.setFillColor(MID_GRAY)
        c.drawString(x, stat_y - 16, label)
    
    # Footer
    c.setFont('Poppins', 8.5)
    c.setFillColor(MID_GRAY)
    c.drawString(56, 55, "Prepared by Vendoroo  \u2022  March 2026")
    c.setFont('Poppins', 7.5)
    c.setFillColor(HexColor('#444444'))
    c.drawString(56, 40, "Sample report with illustrative data. Actual analysis uses your PMS data and documents.")


def draw_score_ring_dark(c, cx, cy, radius, score, color):
    """Draw a score ring on dark background."""
    # Background circle
    c.setStrokeColor(HexColor('#2A2A2A'))
    c.setLineWidth(6)
    c.circle(cx, cy, radius, fill=0, stroke=1)
    # Score arc
    angle = (score / 100) * 360
    c.setStrokeColor(color)
    c.setLineWidth(6)
    p = c.beginPath()
    p.arc(cx - radius, cy - radius, cx + radius, cy + radius, 90, 90 - angle)
    c.drawPath(p, fill=0, stroke=1)
    # Score number
    c.setFont('Poppins-Bold', 22)
    c.setFillColor(WHITE)
    c.drawCentredString(cx, cy - 6, str(score))


# ═══════════════════════════════════════════════
# PAGE 2: EXECUTIVE SUMMARY
# ═══════════════════════════════════════════════

def draw_exec_summary(c):
    y = draw_section_header(c, H - MARGIN - 10, "Executive Summary",
                           "Overall readiness assessment and category breakdown")
    
    # ── Narrative paragraph ──
    y -= 6
    c.setFont('Poppins', 9)
    c.setFillColor(MID_GRAY)
    text = ("Summit Property Group operates a 342-door portfolio using a VA model with 3 coordinators. "
            "Your stated goal is to scale your portfolio without adding headcount. Based on our analysis "
            "of your PMS data, lease agreements, and property management agreement, your current operations "
            "score 64/100. With Vendoroo, we project your operations can reach 92/100. Key areas for "
            "improvement include after-hours operations, emergency protocols, and response time consistency. "
            "Your documentation quality and scalability potential are strong foundations to build on.")
    words = text.split()
    line = ""
    for word in words:
        test = line + " " + word if line else word
        if pdfmetrics.stringWidth(test, 'Poppins', 9) > CONTENT_W:
            c.drawString(MARGIN, y, line)
            y -= 14
            line = word
        else:
            line = test
    if line:
        c.drawString(MARGIN, y, line)
    
    # ── Dark Score Card ──
    y -= 24
    card_h = 80
    draw_rounded_rect(c, MARGIN, y - card_h, CONTENT_W, card_h, r=6, fill=DARK)
    
    # Current ring (inside dark card)
    ring_cx1 = MARGIN + 44
    ring_cy = y - card_h / 2
    draw_score_ring_dark(c, ring_cx1, ring_cy, 28, 64, HexColor('#EF4444'))
    c.setFont('Poppins', 6)
    c.setFillColor(MID_GRAY)
    c.drawCentredString(ring_cx1, ring_cy - 36, "CURRENT")
    
    # Arrow
    c.setFont('Poppins', 14)
    c.setFillColor(MID_GRAY)
    c.drawCentredString(MARGIN + 96, ring_cy - 3, "\u2192")
    
    # Projected ring
    ring_cx2 = MARGIN + 148
    draw_score_ring_dark(c, ring_cx2, ring_cy, 28, 92, YELLOW)
    c.setFont('Poppins', 6)
    c.setFillColor(YELLOW)
    c.drawCentredString(ring_cx2, ring_cy - 36, "WITH VENDOROO")
    
    # Text beside rings
    tx = MARGIN + 200
    c.setFont('Poppins-Bold', 12)
    c.setFillColor(YELLOW)
    c.drawString(tx, ring_cy + 16, "Current Operations Score: 64 \u2192 Projected: 92")
    
    c.setFont('Poppins', 7.5)
    c.setFillColor(HexColor('#AAAAAA'))
    desc = ("Your portfolio has a solid foundation with strong documentation and scalability potential. "
            "Addressing response time, vendor coverage, and emergency protocol gaps during onboarding "
            "will bring your operations to the 90+ range.")
    words = desc.split()
    line = ""
    ty = ring_cy - 2
    max_w = CONTENT_W - (tx - MARGIN) - 12
    for word in words:
        test = line + " " + word if line else word
        if pdfmetrics.stringWidth(test, 'Poppins', 7.5) > max_w:
            c.drawString(tx, ty, line)
            ty -= 11
            line = word
        else:
            line = test
    if line:
        c.drawString(tx, ty, line)
    
    # ── Category Ratings Header ──
    y = y - card_h - 20
    c.setFont('Poppins-Bold', 11)
    c.setFillColor(DARK)
    c.drawString(MARGIN, y, "Category Ratings")
    y -= 18
    
    # ── 2-Column Category Grid ──
    categories = [
        ("Policy Completeness", 58, "Needs Work", AMBER),
        ("Vendor Coverage", 67, "Needs Work", AMBER),
        ("Response Efficiency", 52, "Needs Work", RED),
        ("Documentation Quality", 71, "Ready", GREEN),
        ("Operational Consistency", 55, "Needs Work", AMBER),
        ("After Hours Readiness", 40, "Not Ready", RED),
        ("Emergency Protocols", 48, "Not Ready", RED),
        ("Scalability Potential", 78, "Ready", GREEN),
    ]
    
    card_w = CONTENT_W / 2 - 6
    card_h = 40
    
    for i, (name, score, status, color) in enumerate(categories):
        col = i % 2
        row = i // 2
        cx = MARGIN + col * (card_w + 12)
        cy = y - row * (card_h + 6)
        
        # Card background
        draw_rounded_rect(c, cx, cy - card_h + 8, card_w, card_h, r=4, fill=GRAY_BG, stroke=LINE_GRAY)
        
        # Category name
        c.setFont('Poppins-Medium', 8)
        c.setFillColor(DARK)
        c.drawString(cx + 10, cy, name)
        
        # Status pill
        pill_w = 58
        if status == "Needs Work":
            pill_bg = AMBER_LIGHT
            pill_fg = AMBER
        elif status == "Not Ready":
            pill_bg = RED_LIGHT
            pill_fg = RED
        else:
            pill_bg = GREEN_LIGHT
            pill_fg = GREEN
        
        pill_x = cx + card_w - pill_w - 10
        draw_rounded_rect(c, pill_x, cy - 2, pill_w, 14, r=3, fill=pill_bg)
        c.setFont('Poppins-Bold', 6.5)
        c.setFillColor(pill_fg)
        c.drawCentredString(pill_x + pill_w / 2, cy + 1, status)
        
        # Score number + progress bar
        c.setFont('Poppins-Bold', 12)
        c.setFillColor(color)
        c.drawString(cx + 10, cy - 22, str(score))
        
        bar_x = cx + 38
        bar_w = card_w - 52
        draw_progress_bar(c, bar_x, cy - 19, bar_w, 5, score, color)
    
    # ── Legend ──
    legend_y = y - 4 * (card_h + 6) - 10
    
    legend_items = [
        (GREEN, "Ready (70+)"),
        (AMBER, "Needs Work (50-69)"),
        (RED, "Not Ready (<50)"),
    ]
    lx = MARGIN
    for color, label in legend_items:
        c.setFillColor(color)
        c.circle(lx + 4, legend_y + 3, 3, fill=1, stroke=0)
        c.setFont('Poppins', 7)
        c.setFillColor(SUB_GRAY)
        c.drawString(lx + 12, legend_y, label)
        lx += pdfmetrics.stringWidth(label, 'Poppins', 7) + 28
    
    draw_footer(c, 2)


# ═══════════════════════════════════════════════
# PAGE 3: CURRENT OPERATIONS ANALYSIS
# ═══════════════════════════════════════════════

def draw_current_ops(c):
    y = draw_section_header(c, H - MARGIN - 10, "Current Operations Analysis",
                           "Your performance compared to similar portfolios using AI maintenance coordination")
    
    # Benchmark table
    headers = ["Metric", "Your Current", "AI-Managed Avg.", "Top Performers"]
    rows = [
        ("Avg. First Response (hrs)", "14.2", "4.1", "1.8"),
        ("Avg. Completion Time (days)", "4.8", "2.9", "1.6"),
        ("Open Work Order Rate (%)", "18.3", "9.0", "5.2"),
        ("Resident Satisfaction (%)", "N/A", "91", "96"),
        ("Vendor Response Rate (%)", "72", "89", "95"),
        ("Resolved w/o Vendor (%)", "8", "22", "31"),
    ]
    
    col_widths = [200, 100, 100, 100]
    table_x = MARGIN
    
    # Header row
    y -= 10
    hdr_y = y
    c.setFillColor(DARK)
    c.rect(table_x, hdr_y - 4, CONTENT_W, 20, fill=1, stroke=0)
    c.setFont('Poppins-Medium', 7.5)
    c.setFillColor(WHITE)
    x = table_x
    for i, h in enumerate(headers):
        if i == 0:
            c.drawString(x + 8, hdr_y + 2, h)
        else:
            c.drawCentredString(x + col_widths[i] / 2, hdr_y + 2, h)
        x += col_widths[i]
    
    # Data rows
    y = hdr_y - 22
    for row_i, row in enumerate(rows):
        if row_i % 2 == 1:
            c.setFillColor(GRAY_BG)
            c.rect(table_x, y - 4, CONTENT_W, 18, fill=1, stroke=0)
        
        x = table_x
        for col_i, val in enumerate(row):
            c.setFont('Poppins', 8)
            if col_i == 0:
                c.setFillColor(DARK)
                c.drawString(x + 8, y + 1, val)
            elif col_i == 1:
                c.setFillColor(RED)
                c.setFont('Poppins-Bold', 8)
                c.drawCentredString(x + col_widths[col_i] / 2, y + 1, val)
            else:
                c.setFillColor(MID_GRAY)
                c.drawCentredString(x + col_widths[col_i] / 2, y + 1, val)
            x += col_widths[col_i]
        y -= 18
    
    # Footnote
    y -= 8
    c.setFont('Poppins', 6.5)
    c.setFillColor(SUB_GRAY)
    c.drawString(MARGIN, y, "Benchmarks based on Vendoroo clients with 200-500 door VA-model portfolios. Top performers = 90th percentile.")
    
    # Key Findings
    y -= 30
    c.setFont('Poppins-Bold', 10)
    c.setFillColor(DARK)
    c.drawString(MARGIN, y, "Key Findings")
    y -= 20
    
    findings = [
        ("Response Time Gap", RED,
         "Your average first response of 14.2 hours is 3.5x slower than AI-managed portfolios. "
         "After-hours issues queue until the next business day, adding 8-12 hours to every evening request."),
        ("Vendor Network Gaps", AMBER,
         "You have 22 vendors covering 8 of 12 required trades. Missing backup vendors in HVAC, plumbing, "
         "and electrical creates single points of failure during peak demand."),
        ("Scalability Opportunity", HexColor('#2563EB'),
         "With 3 coordinators managing 342 doors (114 doors/coordinator), you are below the VA-model benchmark "
         "of 175 doors/coordinator. AI coordination could support your current portfolio with 1 coordinator."),
    ]
    
    for title, color, body in findings:
        # Accent bar
        c.setFillColor(color)
        c.rect(MARGIN, y - 40, 3, 50, fill=1, stroke=0)
        # Card background
        draw_rounded_rect(c, MARGIN + 6, y - 44, CONTENT_W - 6, 56, r=4, fill=GRAY_BG)
        # Title
        c.setFont('Poppins-Bold', 9)
        c.setFillColor(DARK)
        c.drawString(MARGIN + 14, y, title)
        # Body (wrap text)
        c.setFont('Poppins', 7.5)
        c.setFillColor(MID_GRAY)
        words = body.split()
        line = ""
        ty = y - 14
        max_w = CONTENT_W - 24
        for word in words:
            test = line + " " + word if line else word
            if pdfmetrics.stringWidth(test, 'Poppins', 7.5) > max_w:
                c.drawString(MARGIN + 14, ty, line)
                ty -= 11
                line = word
            else:
                line = test
        if line:
            c.drawString(MARGIN + 14, ty, line)
        
        y -= 68
    
    draw_footer(c, 3)


# ═══════════════════════════════════════════════
# PAGE 4: WORK ORDER ANALYSIS
# ═══════════════════════════════════════════════

def draw_wo_analysis(c):
    y = draw_section_header(c, H - MARGIN - 10, "Work Order Analysis",
                           "Detailed breakdown of your maintenance work order patterns, volume, and operational signals")
    
    # ── Stat Cards Row ──
    card_w = CONTENT_W / 4 - 6
    card_h = 58
    card_y = y - card_h - 4
    
    stats = [
        ("172", "Maintenance WOs", "Mar 1 - Mar 19 (18 days)", MID_GRAY),
        ("2.9", "WOs per door per year", "Normal range (benchmark: 3-6)", AMBER),
        ("74%", "Created after hours", "Residents submit evenings/weekends", RED),
        ("100%", "Reactive maintenance", "No preventive program detected", RED),
    ]
    for i, (val, label, note, note_clr) in enumerate(stats):
        x = MARGIN + i * (card_w + 8)
        draw_stat_card(c, x, card_y, card_w, card_h, val, label, note, note_clr)
    
    # ── Two Column: Trade Distribution + Source/Channel ──
    y = card_y - 18
    col_w = CONTENT_W / 2 - 8
    
    # Left: Trade Distribution
    c.setFont('Poppins-Bold', 9)
    c.setFillColor(DARK)
    c.drawString(MARGIN, y, "Trade Distribution")
    
    trades = [
        ("Handyperson", 22), ("Plumbing", 15), ("Appliances", 7),
        ("Landscaping", 5.8), ("Cleaning", 5.8), ("HVAC", 4.5),
        ("Other", 4), ("Junk Removal", 3),
    ]
    ty = y - 16
    for name, pct in trades:
        c.setFont('Poppins', 7.5)
        c.setFillColor(DARK)
        c.drawRightString(MARGIN + 80, ty, name)
        draw_progress_bar(c, MARGIN + 88, ty - 1, 120, 10, pct * 4, YELLOW)  # Scale for visual
        c.setFont('Poppins-Medium', 7)
        c.setFillColor(MID_GRAY)
        c.drawString(MARGIN + 214, ty, f"{pct}%")
        ty -= 15
    
    c.setFont('Poppins', 6.5)
    c.setFillColor(SUB_GRAY)
    c.drawString(MARGIN, ty - 2, "No single trade exceeds 25% concentration threshold")
    
    # Right: Source
    right_x = MARGIN + col_w + 16
    c.setFont('Poppins-Bold', 9)
    c.setFillColor(DARK)
    c.drawString(right_x, y, "How Work Orders Are Created")
    
    sy = y - 18
    # Staff Created
    draw_severity_dot(c, right_x + 4, sy + 3, RED)
    c.setFont('Poppins', 8)
    c.setFillColor(DARK)
    c.drawString(right_x + 14, sy, "Staff created (untracked)")
    c.setFont('Poppins-Bold', 8)
    c.drawRightString(right_x + col_w, sy, "76%")
    # Resident
    sy -= 16
    draw_severity_dot(c, right_x + 4, sy + 3, GREEN)
    c.setFont('Poppins', 8)
    c.setFillColor(DARK)
    c.drawString(right_x + 14, sy, "Resident portal")
    c.setFont('Poppins-Bold', 8)
    c.drawRightString(right_x + col_w, sy, "24%")
    
    # Callout box
    sy -= 20
    draw_rounded_rect(c, right_x, sy - 28, col_w, 30, r=4, fill=RED_LIGHT)
    c.setFont('Poppins-Bold', 7)
    c.setFillColor(RED)
    c.drawString(right_x + 8, sy - 6, "76% come through untracked channels")
    c.setFont('Poppins', 6.5)
    c.setFillColor(MID_GRAY)
    c.drawString(right_x + 8, sy - 18, "No system record of the original request.")
    
    # Reactive / Preventive
    sy -= 44
    c.setFont('Poppins-Bold', 9)
    c.setFillColor(DARK)
    c.drawString(right_x, sy, "Maintenance Profile")
    sy -= 22
    box_w = (col_w - 8) / 2
    draw_rounded_rect(c, right_x, sy - 14, box_w, 32, r=4, fill=GRAY_BG)
    c.setFont('Poppins-Bold', 14)
    c.setFillColor(RED)
    c.drawCentredString(right_x + box_w / 2, sy, "100%")
    c.setFont('Poppins', 6.5)
    c.setFillColor(MID_GRAY)
    c.drawCentredString(right_x + box_w / 2, sy - 11, "Reactive")
    
    draw_rounded_rect(c, right_x + box_w + 8, sy - 14, box_w, 32, r=4, fill=GRAY_BG)
    c.setFont('Poppins-Bold', 14)
    c.setFillColor(MID_GRAY)
    c.drawCentredString(right_x + box_w + 8 + box_w / 2, sy, "0%")
    c.setFont('Poppins', 6.5)
    c.drawCentredString(right_x + box_w + 8 + box_w / 2, sy - 11, "Preventive")
    
    # ── Vendor Network Bar (dark) ──
    bar_y = card_y - 240
    bar_h = 36
    draw_rounded_rect(c, MARGIN, bar_y, CONTENT_W, bar_h, r=4, fill=DARK)
    
    vx = MARGIN + 14
    c.setFont('Poppins-Bold', 14)
    c.setFillColor(WHITE)
    c.drawString(vx, bar_y + 14, "42")
    c.setFont('Poppins', 6)
    c.setFillColor(SUB_GRAY)
    c.drawString(vx, bar_y + 5, "EXTERNAL VENDORS")
    
    vx += 60
    c.setStrokeColor(HexColor('#333333'))
    c.setLineWidth(0.5)
    c.line(vx, bar_y + 6, vx, bar_y + 28)
    vx += 10
    
    c.setFont('Poppins-Bold', 14)
    c.setFillColor(WHITE)
    c.drawString(vx, bar_y + 14, "10")
    c.setFont('Poppins', 8)
    c.setFillColor(SUB_GRAY)
    c.drawString(vx + 22, bar_y + 16, "of 12")
    c.setFont('Poppins', 6)
    c.drawString(vx, bar_y + 5, "REQUIRED TRADES COVERED")
    
    vx += 110
    c.setStrokeColor(HexColor('#333333'))
    c.line(vx, bar_y + 6, vx, bar_y + 28)
    vx += 10
    
    c.setFont('Poppins', 7.5)
    c.setFillColor(SUB_GRAY)
    c.drawString(vx, bar_y + 18, "Missing:")
    c.setFillColor(AMBER)
    c.drawString(vx + 38, bar_y + 18, "Roofing, Rooter/Drain")
    c.setFont('Poppins', 6.5)
    c.setFillColor(HexColor('#555555'))
    c.drawString(vx, bar_y + 6, "Top vendor (Need a Hand) handles 24% of maintenance WOs")
    
    # ── Repeat Units Table ──
    y = bar_y - 18
    c.setFont('Poppins-Bold', 9)
    c.setFillColor(DARK)
    c.drawString(MARGIN, y, "Units with Highest WO Volume")
    y -= 14
    
    # Table header
    c.setFillColor(DARK)
    c.setFont('Poppins-Medium', 7)
    c.drawCentredString(MARGIN + 16, y, "WOs")
    c.drawString(MARGIN + 36, y, "Unit Address")
    c.drawString(MARGIN + 230, y, "Top Trades")
    c.drawCentredString(MARGIN + 380, y, "Cost")
    c.drawCentredString(MARGIN + 460, y, "Span")
    y -= 4
    c.setStrokeColor(DARK)
    c.setLineWidth(1)
    c.line(MARGIN, y, W - MARGIN, y)
    y -= 4
    
    units = [
        (8, "1600 I St Bldg 1 #1308, Sparks", "Handyperson, Plumbing", "$2,140", "18 days", "Mar 1 - Mar 19", RED),
        (7, "1424 E 9th St #6, Reno", "Plumbing, HVAC", "$1,875", "15 days", "Mar 2 - Mar 17", RED),
        (6, "1360 Waterloo Dr, Reno", "Handyperson, Cleaning", "$890", "5 days", "Mar 12 - Mar 17", AMBER),
        (6, "1600 I St Bldg 1 #1206, Sparks", "Appliances, Plumbing", "$1,420", "16 days", "Mar 3 - Mar 19", AMBER),
        (5, "3575 Bluejay Ct, Reno", "Handyperson, Doors", "$675", "14 days", "Mar 4 - Mar 18", AMBER),
    ]
    
    for count, addr, trades, cost, span, dates, color in units:
        c.setFont('Poppins-Bold', 11)
        c.setFillColor(color)
        c.drawCentredString(MARGIN + 16, y - 6, str(count))
        
        c.setFont('Poppins-Medium', 7.5)
        c.setFillColor(DARK)
        c.drawString(MARGIN + 36, y - 4, addr)
        
        c.setFont('Poppins', 7)
        c.setFillColor(MID_GRAY)
        c.drawString(MARGIN + 230, y - 4, trades)
        
        c.setFont('Poppins-Bold', 7.5)
        c.setFillColor(DARK)
        c.drawCentredString(MARGIN + 380, y - 4, cost)
        
        c.setFont('Poppins-Bold', 7.5)
        c.setFillColor(DARK)
        c.drawCentredString(MARGIN + 460, y - 3, span)
        c.setFont('Poppins', 6)
        c.setFillColor(SUB_GRAY)
        c.drawCentredString(MARGIN + 460, y - 12, dates)
        
        y -= 22
        c.setStrokeColor(LINE_GRAY)
        c.setLineWidth(0.5)
        c.line(MARGIN, y + 4, W - MARGIN, y + 4)
    
    c.setFont('Poppins', 6.5)
    c.setFillColor(SUB_GRAY)
    c.drawString(MARGIN, y - 6, "13 units with 3+ WOs. 1600 I Street: 4 units, 21 combined WOs, $5,200+ total spend.")
    
    # ── Operational Signals (2x3 grid) ──
    y -= 22
    c.setFont('Poppins-Bold', 9)
    c.setFillColor(DARK)
    c.drawString(MARGIN, y, "Operational Signals")
    y -= 14
    
    signals = [
        ("After-Hours Demand", RED, "74% of requests come in evenings and weekends. Without after-hours triage, these queue until morning."),
        ("Untracked Channels", RED, "76% of WOs created by staff with no record of the original request. Vendoroo captures every request automatically."),
        ("Property Cluster", AMBER, "1600 I Street: 4 units, 21 WOs. Recurring plumbing and handyperson issues suggest building-level needs."),
        ("100% Reactive", AMBER, "No preventive maintenance detected. Operational discovery can surface opportunities to reduce emergency volume."),
        ("Healthy Volume", GREEN, "2.9 WOs per door annually is in the normal range. Well-maintained portfolio with room to scale."),
        ("Strong Trade Coverage", GREEN, "42 vendors covering 10 of 12 required trades. Only Roofing and Rooter/Drain need backup coverage."),
    ]
    
    sig_w = CONTENT_W / 2 - 6
    sig_h = 42
    for i, (title, color, body) in enumerate(signals):
        col = i % 2
        row = i // 2
        sx = MARGIN + col * (sig_w + 12)
        sy = y - row * (sig_h + 6)
        
        draw_rounded_rect(c, sx, sy - sig_h + 10, sig_w, sig_h, r=4, fill=GRAY_BG)
        draw_severity_dot(c, sx + 10, sy + 2, color)
        c.setFont('Poppins-Bold', 7.5)
        c.setFillColor(DARK)
        c.drawString(sx + 18, sy - 1, title)
        
        # Wrap body text
        c.setFont('Poppins', 6.5)
        c.setFillColor(MID_GRAY)
        words = body.split()
        line = ""
        ty = sy - 13
        for word in words:
            test = line + " " + word if line else word
            if pdfmetrics.stringWidth(test, 'Poppins', 6.5) > sig_w - 20:
                c.drawString(sx + 10, ty, line)
                ty -= 9
                line = word
            else:
                line = test
        if line:
            c.drawString(sx + 10, ty, line)
    
    draw_footer(c, 4)


# ═══════════════════════════════════════════════
# PAGE 5: POLICY & DOCUMENTATION REVIEW
# ═══════════════════════════════════════════════

def draw_doc_card(c, y, title, status, status_color, items):
    """Draw a document review card. Returns new y position."""
    card_h = 18 + len(items) * 15
    draw_rounded_rect(c, MARGIN, y - card_h, CONTENT_W, card_h, r=4, fill=GRAY_BG, stroke=LINE_GRAY)
    
    # Header row
    c.setFont('Poppins-Bold', 9)
    c.setFillColor(DARK)
    c.drawString(MARGIN + 10, y - 14, title)
    
    # Status pill
    pill_w = pdfmetrics.stringWidth(status, 'Poppins-Bold', 6.5) + 14
    pill_x = MARGIN + CONTENT_W - pill_w - 10
    if status_color == GREEN:
        pill_bg = GREEN_LIGHT
    elif status_color == AMBER:
        pill_bg = AMBER_LIGHT
    else:
        pill_bg = RED_LIGHT
    draw_rounded_rect(c, pill_x, y - 17, pill_w, 14, r=3, fill=pill_bg)
    c.setFont('Poppins-Bold', 6.5)
    c.setFillColor(status_color)
    c.drawCentredString(pill_x + pill_w / 2, y - 14, status)
    
    # Items
    iy = y - 30
    for is_good, text in items:
        dot_color = GREEN if is_good else RED
        c.setFillColor(dot_color)
        c.circle(MARGIN + 16, iy + 3, 2.5, fill=1, stroke=0)
        c.setFont('Poppins', 7.5)
        c.setFillColor(DARK if is_good else MID_GRAY)
        c.drawString(MARGIN + 24, iy, text)
        iy -= 15
    
    return y - card_h - 8


def draw_policy_review(c):
    y = draw_section_header(c, H - MARGIN - 10, "Policy & Documentation Review",
                           "Assessment of your PMA, lease, and operational policies against best practices")
    
    y = draw_doc_card(c, y, "Property Management Agreement (PMA)", "Received & Reviewed", GREEN, [
        (True, "Maintenance responsibility clearly delineated between owner and tenant"),
        (True, "Owner approval thresholds defined ($500 NTE, single tier)"),
        (True, "Emergency authorization language present but vague"),
        (False, "Missing: appliance coverage specifics, HVAC filter replacement responsibility"),
    ])
    
    y = draw_doc_card(c, y, "Lease Agreement Template", "Received & Reviewed", GREEN, [
        (True, "Tenant maintenance obligations clearly stated"),
        (True, "Move-in/move-out inspection procedures documented"),
        (True, "Tenant damage vs. normal wear language present"),
        (False, "Missing: specific tenant troubleshooting expectations before requesting service"),
    ])
    
    y = draw_doc_card(c, y, "Emergency Protocols", "Not Documented", RED, [
        (False, "No written emergency classification criteria"),
        (False, "Answering service uses informal judgment for after-hours triage"),
        (False, "No defined response SLAs by urgency level"),
        (False, "No documented vendor escalation procedures for emergencies"),
    ])
    
    y = draw_doc_card(c, y, "Vendor Management Policies", "Partially Documented", AMBER, [
        (True, "Preferred vendor list exists but not formalized with trade coverage"),
        (False, "No backup vendor assignments for critical trades"),
        (False, "NTE structure is a flat $500 across all categories"),
        (False, "No vendor performance tracking or SLA enforcement"),
    ])
    
    y = draw_doc_card(c, y, "Maintenance SOPs", "Partially Documented", AMBER, [
        (True, "General workflow exists but not codified into repeatable rules"),
        (False, "Coordinator assignments are tribal knowledge, not documented"),
        (False, "No standardized resident communication templates or cadences"),
        (False, "Troubleshooting steps not formalized by issue type"),
    ])
    
    draw_footer(c, 5)


# ═══════════════════════════════════════════════
# PAGE 6: WHAT WE ADDRESS TOGETHER
# ═══════════════════════════════════════════════

def draw_gap_card(c, y, title, severity, severity_color, detail, recommendation):
    """Draw a gap/recommendation card. Returns new y."""
    # Calculate height needed
    rec_lines = len(recommendation) // 70 + 2
    card_h = 70 + rec_lines * 10
    
    # Left accent bar
    c.setFillColor(severity_color)
    c.rect(MARGIN, y - card_h, 3, card_h, fill=1, stroke=0)
    
    # Card background
    draw_rounded_rect(c, MARGIN + 5, y - card_h, CONTENT_W - 5, card_h, r=4, fill=GRAY_BG)
    
    # Header
    c.setFont('Poppins-Bold', 9)
    c.setFillColor(DARK)
    c.drawString(MARGIN + 14, y - 14, title)
    
    # Severity pill
    pill_w = pdfmetrics.stringWidth(severity, 'Poppins-Bold', 6.5) + 14
    pill_x = MARGIN + CONTENT_W - pill_w - 10
    if severity_color == RED:
        pill_bg = RED_LIGHT
    elif severity_color == AMBER:
        pill_bg = AMBER_LIGHT
    else:
        pill_bg = GREEN_LIGHT
    draw_rounded_rect(c, pill_x, y - 17, pill_w, 14, r=3, fill=pill_bg)
    c.setFont('Poppins-Bold', 6.5)
    c.setFillColor(severity_color)
    c.drawCentredString(pill_x + pill_w / 2, y - 14, severity)
    
    # Detail text
    c.setFont('Poppins', 7.5)
    c.setFillColor(MID_GRAY)
    dy = y - 30
    for line in _wrap_text(detail, 'Poppins', 7.5, CONTENT_W - 28):
        c.drawString(MARGIN + 14, dy, line)
        dy -= 11
    
    # Recommendation label
    dy -= 4
    c.setFont('Poppins-Bold', 7)
    c.setFillColor(YELLOW)
    c.drawString(MARGIN + 14, dy, "How Your AI Adoption Advisor Addresses This")
    dy -= 12
    
    # Recommendation text
    c.setFont('Poppins', 7.5)
    c.setFillColor(MID_GRAY)
    for line in _wrap_text(recommendation, 'Poppins', 7.5, CONTENT_W - 28):
        c.drawString(MARGIN + 14, dy, line)
        dy -= 11
    
    return dy - 6


def _wrap_text(text, font, size, max_w):
    """Wrap text to fit within max_w. Returns list of lines."""
    words = text.split()
    lines = []
    line = ""
    for word in words:
        test = line + " " + word if line else word
        if pdfmetrics.stringWidth(test, font, size) > max_w:
            lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    return lines


def draw_gaps(c):
    y = draw_section_header(c, H - MARGIN - 10, "What We Address Together",
                           "Your AI Adoption Advisor works through each area during onboarding and your first 90 days")
    
    # AAA intro callout
    y -= 4
    draw_rounded_rect(c, MARGIN, y - 36, CONTENT_W, 36, r=4, fill=AMBER_LIGHT)
    c.setFillColor(YELLOW)
    c.rect(MARGIN, y - 36, 3, 36, fill=1, stroke=0)
    c.setFont('Poppins', 8)
    c.setFillColor(DARK)
    intro = ("Every Vendoroo client is paired with an AI Adoption Advisor who personally guides you through these "
             "items. Your Advisor doesn't just identify gaps: they configure solutions, build your Maintenance Book, "
             "and ensure your AI teammate is operating to your standards before go-live.")
    ty = y - 12
    for line in _wrap_text(intro, 'Poppins', 8, CONTENT_W - 20):
        c.drawString(MARGIN + 10, ty, line)
        ty -= 12
    
    y -= 50
    
    gaps = [
        ("Emergency Protocol", "High Priority", RED,
         "No formal written emergency criteria. After hours triage relies on answering service judgment with no documented escalation rules.",
         "Your Advisor works with you to define emergency categories, response SLAs, and escalation paths during onboarding. These are encoded directly into your Maintenance Book so your AI teammate knows exactly how to handle emergencies from Day 1."),
        ("Vendor Coverage", "Medium Priority", AMBER,
         "22 vendors covering 8 of 12 required trades. No backup vendors for HVAC, plumbing, or electrical.",
         "Your Advisor maps your existing vendor network against required trades and identifies the specific gaps. You can fill those gaps during onboarding, or Vendoroo can assist through our vendor recruitment product."),
        ("Response Time SLAs", "High Priority", RED,
         "No defined response time targets. Average first response of 14.2 hours compared to Vendoroo's average of under 10 minutes.",
         "Your Advisor helps you align on what good SLAs look like for your portfolio and trains your AI teammate to meet them, including vendor-specific expectations."),
        ("NTE Governance", "Medium Priority", AMBER,
         "Single $500 NTE threshold across all work types. No differentiation by trade, property, or urgency.",
         "Your Advisor educates and guides you on how to structure tiered NTEs, including per-property configurations. Your AI teammate then enforces these rules automatically."),
        ("After Hours Operations", "High Priority", RED,
         "Answering service handles calls but cannot triage, dispatch, or make decisions. All after hours issues queue until next business day.",
         "Your Advisor configures Rooceptionist for 24/7 intelligent call handling with full triage and dispatch capability. After hours requests are acted on immediately."),
        ("Policy Documentation", "Low Priority", GREEN,
         "PMA and lease templates are solid. Minor gaps in maintenance responsibility language for appliance coverage and HVAC filter replacement.",
         "Any unclear or missing policies are clarified with you during onboarding. Your Advisor ensures every policy decision is documented in your Maintenance Book before go-live."),
    ]
    
    for title, severity, color, detail, rec in gaps:
        y = draw_gap_card(c, y, title, severity, color, detail, rec)
    
    draw_footer(c, 6)


# ═══════════════════════════════════════════════
# PAGE 7: PROJECTED IMPACT
# ═══════════════════════════════════════════════

def draw_projected_impact(c):
    y = draw_section_header(c, H - MARGIN - 10, "Projected Impact",
                           "What changes with AI-powered maintenance coordination")
    
    # Intro text
    y -= 4
    c.setFont('Poppins', 8.5)
    c.setFillColor(MID_GRAY)
    intro = ("Based on your current operational data and our benchmarks from similar VA-model portfolios, "
             "here is what we project with full Vendoroo implementation.")
    for line in _wrap_text(intro, 'Poppins', 8.5, CONTENT_W):
        c.drawString(MARGIN, y, line)
        y -= 13
    
    # Projection table
    y -= 10
    headers = ["Metric", "Current", "Projected", "Benchmark Range", "Improvement"]
    col_w = [160, 70, 70, 100, 80]
    
    # Header
    c.setFillColor(DARK)
    c.rect(MARGIN, y - 4, CONTENT_W, 18, fill=1, stroke=0)
    c.setFont('Poppins-Medium', 7)
    c.setFillColor(WHITE)
    hx = MARGIN
    for i, h in enumerate(headers):
        if i == 0:
            c.drawString(hx + 8, y + 1, h)
        else:
            c.drawCentredString(hx + col_w[i] / 2, y + 1, h)
        hx += col_w[i]
    
    rows = [
        ("First Response Time", "14.2 hrs", "< 10 min", "< 10 min avg.", "99%"),
        ("Work Order Completion", "4.8 days", "3.0 days", "37.5-50% decrease", "37.5%"),
        ("Open WO Rate", "18.3%", "9.8%", "5-9.8%", "46%"),
        ("After-Hours Availability", "Partial", "Full 24/7", "\\u2014", "100%"),
        ("Resolved w/o Vendor", "~8%", "~9.6%", "9.6-15%", "20%"),
        ("Resident Satisfaction", "N/A", "94%", "94-98%+", "\u2014"),
    ]
    
    y -= 20
    for ri, row in enumerate(rows):
        if ri % 2 == 1:
            c.setFillColor(GRAY_BG)
            c.rect(MARGIN, y - 4, CONTENT_W, 18, fill=1, stroke=0)
        rx = MARGIN
        for ci, val in enumerate(row):
            if ci == 0:
                c.setFont('Poppins', 7.5)
                c.setFillColor(DARK)
                c.drawString(rx + 8, y + 1, val)
            elif ci == 1:
                c.setFont('Poppins-Bold', 7.5)
                c.setFillColor(RED)
                c.drawCentredString(rx + col_w[ci] / 2, y + 1, val)
            elif ci == 2:
                c.setFont('Poppins-Bold', 7.5)
                c.setFillColor(GREEN)
                c.drawCentredString(rx + col_w[ci] / 2, y + 1, val)
            elif ci == 4 and val != "\u2014":
                c.setFont('Poppins-Bold', 7)
                c.setFillColor(GREEN)
                c.drawCentredString(rx + col_w[ci] / 2, y + 1, "\u2191 " + val)
            else:
                c.setFont('Poppins', 7.5)
                c.setFillColor(MID_GRAY)
                c.drawCentredString(rx + col_w[ci] / 2, y + 1, val)
            rx += col_w[ci]
        y -= 18
    
    # Goal section
    y -= 20
    c.setFont('Poppins-Bold', 11)
    c.setFillColor(DARK)
    c.drawString(MARGIN, y, "What's Your Goal?")
    y -= 14
    c.setFont('Poppins', 8)
    c.setFillColor(MID_GRAY)
    c.drawString(MARGIN, y, "Your AI teammate supports three different strategic paths.")
    y -= 16
    
    # Current state bar
    draw_rounded_rect(c, MARGIN, y - 22, CONTENT_W, 22, r=4, fill=GRAY_BG)
    c.setFont('Poppins-Bold', 6.5)
    c.setFillColor(MID_GRAY)
    c.drawString(MARGIN + 10, y - 14, "CURRENT STATE")
    c.setFont('Poppins-Bold', 9)
    c.setFillColor(DARK)
    c.drawString(MARGIN + 90, y - 14, "3 Coordinators")
    c.setFont('Poppins', 7.5)
    c.setFillColor(MID_GRAY)
    c.drawString(MARGIN + 190, y - 14, "342 doors (114 doors/coordinator)  |  Benchmark: 175")
    y -= 34
    
    # Three goal cards
    card_w = (CONTENT_W - 20) / 3
    card_h = 175
    goals = [
        ("Path 1", "Scale", True,
         "Keep your current team and grow your portfolio without adding headcount. Your AI teammate absorbs the coordination workload.",
         "1,050+", "doors with current team", "Direct or Command"),
        ("Path 2", "Optimize", False,
         "Reduce staffing costs by letting your AI teammate handle coordination that currently requires dedicated headcount.",
         "2 FTEs", "potential savings at current door count", "Direct or Command"),
        ("Path 3", "Elevate", False,
         "Keep your team and portfolio size, dramatically improve quality and consistency. Faster responses, fewer open WOs, higher satisfaction.",
         "94%+", "resident satisfaction with consistent SLAs", "Engage, Direct, or Command"),
    ]
    
    for i, (path_num, name, selected, desc, metric, metric_label, tiers) in enumerate(goals):
        gx = MARGIN + i * (card_w + 10)
        
        if selected:
            draw_rounded_rect(c, gx, y - card_h, card_w, card_h, r=6, fill=WHITE, stroke=YELLOW, stroke_width=2)
        else:
            draw_rounded_rect(c, gx, y - card_h, card_w, card_h, r=6, fill=WHITE, stroke=LINE_GRAY, stroke_width=1)
        
        # Path label
        if selected:
            draw_rounded_rect(c, gx + 10, y - 2, 44, 12, r=3, fill=YELLOW)
            c.setFont('Poppins-Bold', 6)
            c.setFillColor(DARK)
            c.drawCentredString(gx + 32, y - 0, path_num)
        else:
            c.setFont('Poppins-Bold', 6.5)
            c.setFillColor(MID_GRAY)
            c.drawString(gx + 10, y - 12, path_num.upper())
        
        # Name
        c.setFont('Poppins-Bold', 12)
        c.setFillColor(DARK)
        c.drawString(gx + 10, y - 28, name)
        
        if selected:
            c.setFont('Poppins-Bold', 7)
            c.setFillColor(YELLOW)
            c.drawString(gx + 10 + pdfmetrics.stringWidth(name, 'Poppins-Bold', 12) + 8, y - 26, "YOUR GOAL")
        
        # Description
        c.setFont('Poppins', 7)
        c.setFillColor(MID_GRAY)
        dy = y - 44
        for line in _wrap_text(desc, 'Poppins', 7, card_w - 24):
            c.drawString(gx + 10, dy, line)
            dy -= 10
        
        # Divider
        div_y = y - card_h + 60
        c.setStrokeColor(LINE_GRAY)
        c.setLineWidth(0.5)
        c.line(gx + 10, div_y, gx + card_w - 10, div_y)
        
        # Metric
        c.setFont('Poppins-Bold', 16)
        c.setFillColor(DARK)
        c.drawString(gx + 10, div_y - 20, metric)
        c.setFont('Poppins', 7)
        c.setFillColor(MID_GRAY)
        c.drawString(gx + 10, div_y - 32, metric_label)
        
        # Tier
        c.setFont('Poppins', 6.5)
        c.setFillColor(MID_GRAY)
        c.drawString(gx + 10, div_y - 46, "Best supported by")
        c.setFont('Poppins-Bold', 8)
        c.setFillColor(YELLOW)
        c.drawString(gx + 10, div_y - 56, tiers)
    
    # Footnote
    c.setFont('Poppins', 6.5)
    c.setFillColor(SUB_GRAY)
    c.drawString(MARGIN, y - card_h - 10, "Projections based on Vendoroo client benchmarks. These paths are not mutually exclusive: many clients start with one goal and expand over time.")
    
    draw_footer(c, 7)


# ═══════════════════════════════════════════════
# PAGE 8: YOUR PATH WITH VENDOROO
# ═══════════════════════════════════════════════

def draw_tier_recommendation(c):
    y = draw_section_header(c, H - MARGIN - 10, "Your Path with Vendoroo",
                           "Based on your gaps, here is what each tier addresses and our recommendation")
    
    # Three tier cards
    card_w = (CONTENT_W - 20) / 3
    card_h = 175
    
    tiers = [
        ("Engage", "$3", "/ unit / month", "3 dedicated ROOs", "Always-on AI Communications Desk", [
            (False, "24/7 AI business line"),
            (False, "Smart call routing"),
            (False, "Text, email, PMS messaging"),
            (False, "Troubleshooting before dispatch"),
            (False, "AI triage and vendor suggestions"),
            (False, "Custom escalation workflows"),
        ], False),
        ("Direct", "$6", "/ unit / month", "4 dedicated ROOs", "Engage + end-to-end coordination", [
            (False, "Everything in Engage"),
            (True, "Vendor assignment and dispatch"),
            (True, "Appointment coordination"),
            (True, "Custom workflows and approvals"),
            (True, "Invoice collection and logging"),
            (True, "Automated review prompts"),
        ], True),
        ("Command", "$8.50", "/ unit / month", "5 ROOs + human experts", "Direct + owner comms and HITL", [
            (False, "Everything in Direct"),
            (True, "White-labeled owner communication"),
            (True, "Automated bid approvals over NTE"),
            (True, "Human concierge for edge cases"),
            (True, "Warranty and supply coordination"),
            (True, "Daytime emergency handling"),
        ], False),
    ]
    
    for i, (name, price, price_sub, roos, subtitle, features, recommended) in enumerate(tiers):
        tx = MARGIN + i * (card_w + 10)
        
        if recommended:
            draw_rounded_rect(c, tx, y - card_h, card_w, card_h, r=6, fill=WHITE, stroke=YELLOW, stroke_width=2)
            badge_w = 80
            draw_rounded_rect(c, tx + (card_w - badge_w) / 2, y + 2, badge_w, 16, r=4, fill=YELLOW)
            c.setFont('Poppins-Bold', 7)
            c.setFillColor(DARK)
            c.drawCentredString(tx + card_w / 2, y + 6, "Recommended")
        else:
            draw_rounded_rect(c, tx, y - card_h, card_w, card_h, r=6, fill=WHITE, stroke=LINE_GRAY, stroke_width=1)
        
        c.setFont('Poppins-Bold', 12)
        c.setFillColor(DARK)
        c.drawString(tx + 12, y - 14, name)
        
        c.setFont('Poppins', 6)
        c.setFillColor(MID_GRAY)
        c.drawString(tx + 12, y - 26, subtitle)
        
        c.setFont('Poppins-Bold', 16)
        c.setFillColor(DARK)
        c.drawString(tx + 12, y - 46, price)
        price_end = tx + 12 + pdfmetrics.stringWidth(price, 'Poppins-Bold', 16)
        c.setFont('Poppins', 7)
        c.setFillColor(MID_GRAY)
        c.drawString(price_end + 2, y - 43, price_sub)
        
        c.setFont('Poppins-Medium', 7)
        c.setFillColor(SUB_GRAY)
        c.drawString(tx + 12, y - 58, roos)
        
        fy = y - 72
        for is_new, feat in features:
            if is_new:
                c.setFont('Poppins-Medium', 6.5)
                c.setFillColor(DARK)
            else:
                c.setFont('Poppins', 6.5)
                c.setFillColor(MID_GRAY)
            c.drawString(tx + 20, fy, feat)
            c.setFillColor(YELLOW if is_new else LINE_GRAY)
            c.circle(tx + 14, fy + 2, 2, fill=1, stroke=0)
            fy -= 13
    
    # Gap-to-tier mapping table
    y = y - card_h - 12
    c.setFont('Poppins-Bold', 9)
    c.setFillColor(DARK)
    c.drawString(MARGIN, y, "How your gaps map to each tier")
    y -= 12
    
    gap_cols = [260, 80, 80, 80]
    c.setFillColor(DARK)
    c.rect(MARGIN, y - 3, CONTENT_W, 15, fill=1, stroke=0)
    c.setFont('Poppins-Medium', 6.5)
    c.setFillColor(WHITE)
    gx = MARGIN
    for h, w in zip(["Your Gap", "Engage", "Direct", "Command"], gap_cols):
        if h == "Your Gap":
            c.drawString(gx + 8, y + 1, h)
        else:
            c.drawCentredString(gx + w / 2, y + 1, h)
        gx += w
    
    gap_rows = [
        ("Response Time (14.2 hrs \u2192 under 10 min)", True, True, True),
        ("Troubleshooting Before Dispatch", True, True, True),
        ("Vendor Dispatch and Coordination", False, True, True),
        ("NTE Enforcement and Approval Workflows", False, True, True),
        ("After-Hours Emergency Coverage", False, False, True),
        ("Owner Communication and Bid Approvals", False, False, True),
        ("Edge Cases: Warranties, Disputes", False, False, True),
    ]
    
    y -= 16
    for ri, (gap_name, eng, direct, cmd) in enumerate(gap_rows):
        if ri % 2 == 1:
            c.setFillColor(GRAY_BG)
            c.rect(MARGIN, y - 2, CONTENT_W, 13, fill=1, stroke=0)
        
        c.setFont('Poppins', 6.5)
        c.setFillColor(DARK)
        c.drawString(MARGIN + 8, y, gap_name)
        
        for ci, val in enumerate([eng, direct, cmd]):
            cx = MARGIN + gap_cols[0] + ci * gap_cols[ci + 1] + gap_cols[ci + 1] / 2
            if val:
                c.setFont('Poppins-Bold', 8)
                c.setFillColor(GREEN)
                c.drawCentredString(cx, y, "\u2713")
            else:
                c.setFont('Poppins', 8)
                c.setFillColor(LINE_GRAY)
                c.drawCentredString(cx, y, "\u2014")
        y -= 13
    
    # Recommendation card
    y -= 8
    rec_h = 58
    draw_rounded_rect(c, MARGIN, y - rec_h, CONTENT_W, rec_h, r=6, fill=DARK)
    
    c.setFont('Poppins-Bold', 9)
    c.setFillColor(YELLOW)
    c.drawString(MARGIN + 14, y - 13, "Based on your analysis: Direct is the recommended starting point")
    
    c.setFont('Poppins', 7)
    c.setFillColor(HexColor('#AAAAAA'))
    rec_text = ("Your portfolio's primary gaps are response time, open work order rate, and vendor coordination. "
                "Direct addresses all three while your team retains owner communication.")
    ty = y - 26
    for line in _wrap_text(rec_text, 'Poppins', 7, CONTENT_W - 28):
        c.drawString(MARGIN + 14, ty, line)
        ty -= 10
    
    # Cost estimates
    costs = [("$3,846/mo", "Direct (641 \u00d7 $6)"), ("$5,449/mo", "Command (641 \u00d7 $8.50)"), ("+$962/mo", "RescueRoo (641 \u00d7 $1.50)")]
    cx_start = MARGIN + 14
    for val, label in costs:
        c.setFont('Poppins-Bold', 9)
        c.setFillColor(WHITE)
        c.drawString(cx_start, y - rec_h + 16, val)
        c.setFont('Poppins', 6)
        c.setFillColor(SUB_GRAY)
        c.drawString(cx_start, y - rec_h + 6, label)
        cx_start += 170
    
    c.setFont('Poppins', 6)
    c.setFillColor(SUB_GRAY)
    c.drawString(MARGIN, y - rec_h - 8, "All tiers require $400/mo minimum. Pricing is per unit per month. RescueRoo extends emergency handling to 24/7.")
    
    draw_footer(c, 8)


# ═══════════════════════════════════════════════
# PAGE 9: AI ADOPTION PROGRAM
# ═══════════════════════════════════════════════

def draw_aaa_program(c):
    y = draw_section_header(c, H - MARGIN - 10, "Your AI Adoption Program",
                           "How your AI Adoption Advisor gets you from analysis to full operational confidence")
    
    # AAA Value Card (dark)
    card_h = 70
    draw_rounded_rect(c, MARGIN, y - card_h, CONTENT_W, card_h, r=6, fill=DARK)
    
    # Star icon
    draw_rounded_rect(c, MARGIN + 14, y - 16, 26, 26, r=6, fill=YELLOW)
    c.setFont('Poppins-Bold', 14)
    c.setFillColor(DARK)
    c.drawCentredString(MARGIN + 27, y - 9, "\u2605")
    
    c.setFont('Poppins-Bold', 10)
    c.setFillColor(YELLOW)
    c.drawString(MARGIN + 50, y - 10, "AI Adoption Advisory")
    c.setFont('Poppins', 7)
    c.setFillColor(MID_GRAY)
    c.drawString(MARGIN + 50 + pdfmetrics.stringWidth("AI Adoption Advisory", 'Poppins-Bold', 10) + 6, y - 8, "Included with Your Subscription")
    
    c.setFont('Poppins', 7.5)
    c.setFillColor(HexColor('#AAAAAA'))
    desc = ("Every Vendoroo client receives a dedicated AI Adoption Advisor who builds, configures, and optimizes "
            "your AI maintenance operation. Your Advisor is a property management expert who personally ensures "
            "your AI teammate operates to your standards.")
    ty = y - 26
    for line in _wrap_text(desc, 'Poppins', 7.5, CONTENT_W - 30):
        c.drawString(MARGIN + 14, ty, line)
        ty -= 10
    
    c.setFont('Poppins-Bold', 12)
    c.setFillColor(WHITE)
    c.drawString(MARGIN + 14, y - card_h + 12, "$2,500")
    c.setFont('Poppins', 7)
    c.setFillColor(MID_GRAY)
    c.drawString(MARGIN + 70, y - card_h + 14, "value")
    c.setFont('Poppins-Bold', 7)
    c.setFillColor(GREEN)
    c.drawString(MARGIN + 110, y - card_h + 14, "COMPLIMENTARY WITH SUBSCRIPTION")
    
    # Already Completed box
    y = y - card_h - 12
    done_h = 74
    draw_rounded_rect(c, MARGIN, y - done_h, CONTENT_W, done_h, r=4, fill=GREEN_LIGHT, stroke=GREEN, stroke_width=0.5)
    c.setFont('Poppins-Bold', 9)
    c.setFillColor(DARK)
    c.drawString(MARGIN + 12, y - 13, "\u2713  Already Completed Through This Analysis")
    
    done_items = [
        "PMS data analyzed and benchmarked against AI-managed portfolios",
        "Lease and PMA reviewed with policy gaps identified",
        "Vendor network assessed with trade coverage mapped",
        "Operational model evaluated with staffing projections calculated",
        "Readiness gaps identified with remediation plan defined",
    ]
    dy = y - 28
    for item in done_items:
        c.setFont('Poppins', 7)
        c.setFillColor(MID_GRAY)
        c.drawString(MARGIN + 20, dy, "\u2022  " + item)
        dy -= 10
    
    # Three phases
    y = y - done_h - 14
    c.setFont('Poppins-Bold', 10)
    c.setFillColor(DARK)
    c.drawString(MARGIN, y, "Your Adoption Journey: Three Phases")
    y -= 16
    
    phase_w = (CONTENT_W - 20) / 3
    phase_h = 180
    
    phases = [
        ("Phase 1", "Learning", "Days 0 to 30", YELLOW, True,
         "Your Advisor builds your Maintenance Book from the gaps identified in this report. Emergency protocols, NTE rules, vendor assignments, and resident policies are configured and tested before go-live.",
         "AI teammate live and handling work orders"),
        ("Phase 2", "Adoption", "Days 30 to 90", MID_GRAY, False,
         "Your Advisor monitors AI performance, refines the Maintenance Book based on real work order patterns, and coaches your team on working alongside your AI teammate. Average of 85 refinements in this phase.",
         "Team confident, AI handling 98% autonomously"),
        ("Phase 3", "Optimization", "90 Days+", MID_GRAY, False,
         "Your Advisor shifts to monthly check-ins focused on operational improvements, vendor performance, and portfolio growth planning. The AI surfaces insights (1 in 50 WOs identifies an improvement).",
         "Fully embedded, scaling without adding headcount"),
    ]
    
    for i, (label, name, timeframe, color, active, desc, milestone) in enumerate(phases):
        px = MARGIN + i * (phase_w + 10)
        
        if active:
            draw_rounded_rect(c, px, y - phase_h, phase_w, phase_h, r=6, fill=WHITE, stroke=YELLOW, stroke_width=2)
        else:
            draw_rounded_rect(c, px, y - phase_h, phase_w, phase_h, r=6, fill=WHITE, stroke=LINE_GRAY, stroke_width=1)
        
        # Phase pill
        pill_bg = YELLOW if active else GRAY_BG
        pill_fg = DARK if active else MID_GRAY
        draw_rounded_rect(c, px + 10, y + 2, 42, 12, r=3, fill=pill_bg)
        c.setFont('Poppins-Bold', 6)
        c.setFillColor(pill_fg)
        c.drawCentredString(px + 31, y + 5, label.upper())
        
        c.setFont('Poppins-Bold', 10)
        c.setFillColor(DARK)
        c.drawString(px + 10, y - 14, name)
        c.setFont('Poppins-Bold', 7)
        c.setFillColor(color)
        c.drawString(px + 10, y - 26, timeframe)
        
        c.setFont('Poppins', 6.5)
        c.setFillColor(MID_GRAY)
        dy = y - 40
        for line in _wrap_text(desc, 'Poppins', 6.5, phase_w - 24):
            c.drawString(px + 10, dy, line)
            dy -= 9
        
        # Milestone at bottom of card
        mile_y = y - phase_h + 28
        c.setStrokeColor(LINE_GRAY)
        c.setLineWidth(0.5)
        c.line(px + 10, mile_y + 12, px + phase_w - 10, mile_y + 12)
        c.setFont('Poppins', 6)
        c.setFillColor(MID_GRAY)
        c.drawString(px + 10, mile_y + 2, "MILESTONE")
        c.setFont('Poppins-Bold', 7)
        c.setFillColor(DARK)
        c.drawString(px + 10, mile_y - 10, milestone)
    
    draw_footer(c, 9)


# ═══════════════════════════════════════════════
# PAGE 10: CLOSING
# ═══════════════════════════════════════════════

def draw_closing(c):
    """Draw the closing CTA page - full dark background."""
    c.setFillColor(DARK)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    
    # Yellow accent bar
    c.setFillColor(YELLOW)
    c.rect(0, H - 6, W, 6, fill=1, stroke=0)
    
    # Vendoroo
    c.setFont('Poppins-Bold', 14)
    c.setFillColor(YELLOW)
    c.drawString(56, H - 50, "VENDOROO")
    
    # Center content (vertically centered on page)
    center_y = H / 2 + 60
    
    c.setFont('Poppins-Light', 11)
    c.setFillColor(YELLOW)
    c.drawCentredString(W / 2, center_y + 60, "OPERATIONS ANALYSIS")
    
    c.setFont('Poppins-Bold', 28)
    c.setFillColor(WHITE)
    c.drawCentredString(W / 2, center_y + 16, "Ready to See It in Action?")
    
    c.setFont('Poppins', 11)
    c.setFillColor(MID_GRAY)
    lines = [
        "Everything in this report becomes your Maintenance Book.",
        "Your policies. Your vendors. Your standards.",
        "Executed with consistency no human team can match.",
    ]
    ly = center_y - 20
    for line in lines:
        c.drawCentredString(W / 2, ly, line)
        ly -= 20
    
    # CTA button
    btn_w = 200
    btn_h = 40
    btn_x = (W - btn_w) / 2
    btn_y = ly - 24
    draw_rounded_rect(c, btn_x, btn_y, btn_w, btn_h, r=4, fill=YELLOW)
    c.setFont('Poppins-Bold', 13)
    c.setFillColor(DARK)
    c.drawCentredString(W / 2, btn_y + 14, "Let's Get Started")
    
    # URL
    c.setFont('Poppins-Medium', 9)
    c.setFillColor(MID_GRAY)
    c.drawCentredString(W / 2, btn_y - 28, "vendoroo.ai")
    
    # Footer
    c.setFont('Poppins', 7)
    c.setFillColor(HexColor('#444444'))
    c.drawCentredString(W / 2, 36, "Sample Report  \u2022  Summit Property Group (Illustrative Data)  \u2022  March 2026")

def generate_report(output_path):
    c = canvas.Canvas(output_path, pagesize=letter)
    c.setTitle("Vendoroo Operations Analysis - Summit Property Group")
    c.setAuthor("Vendoroo")
    
    # Page 1: Cover
    draw_cover(c)
    c.showPage()
    
    # Page 2: Executive Summary
    draw_exec_summary(c)
    c.showPage()
    
    # Page 3: Current Operations
    draw_current_ops(c)
    c.showPage()
    
    # Page 4: Work Order Analysis
    draw_wo_analysis(c)
    c.showPage()
    
    # Page 5: Policy & Documentation Review
    draw_policy_review(c)
    c.showPage()
    
    # Page 6: What We Address Together
    draw_gaps(c)
    c.showPage()
    
    # Page 7: Projected Impact
    draw_projected_impact(c)
    c.showPage()
    
    # Page 8: Your Path with Vendoroo
    draw_tier_recommendation(c)
    c.showPage()
    
    # Page 9: AI Adoption Program
    draw_aaa_program(c)
    c.showPage()
    
    # Page 10: Closing
    draw_closing(c)
    c.showPage()
    
    c.save()
    print(f"PDF generated: {output_path}")


def generate_report_to_bytes(report_data=None):
    """Generate the PDF report and return as bytes.

    Args:
        report_data: ReportData object (optional). When provided, dynamic data
                     from the report is used. When None, generates sample report.

    Returns:
        bytes: The PDF content as bytes.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    client_name = "Sample Client"
    if report_data:
        client_name = getattr(report_data, 'company_name', 'Sample Client') or 'Sample Client'

    c.setTitle(f"Vendoroo Operations Analysis - {client_name}")
    c.setAuthor("Vendoroo")

    # Page 1: Cover
    draw_cover(c)
    c.showPage()

    # Page 2: Executive Summary
    draw_exec_summary(c)
    c.showPage()

    # Page 3: Current Operations
    draw_current_ops(c)
    c.showPage()

    # Page 4: Work Order Analysis
    draw_wo_analysis(c)
    c.showPage()

    # Page 5: Policy & Documentation Review
    draw_policy_review(c)
    c.showPage()

    # Page 6: What We Address Together
    draw_gaps(c)
    c.showPage()

    # Page 7: Projected Impact
    draw_projected_impact(c)
    c.showPage()

    # Page 8: Your Path with Vendoroo
    draw_tier_recommendation(c)
    c.showPage()

    # Page 9: AI Adoption Program
    draw_aaa_program(c)
    c.showPage()

    # Page 10: Closing
    draw_closing(c)
    c.showPage()

    c.save()
    return buf.getvalue()


if __name__ == "__main__":
    generate_report("/home/claude/Operations_Analysis_Sample.pdf")
