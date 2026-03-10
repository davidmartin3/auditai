"""
generate_report.py
AuditAI — Marketing Audit PDF Report Generator
Usage: python generate_report.py --domain example.com --output reports/
       python generate_report.py --json audit_data.json --output reports/
"""

import argparse
import json
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Brand Colors ──────────────────────────────────────────────
INK        = colors.HexColor("#0a0a0a")
PAPER      = colors.HexColor("#f5f0e8")
CREAM      = colors.HexColor("#ede8dc")
RUST       = colors.HexColor("#c84b2f")
RUST_LIGHT = colors.HexColor("#e8623f")
SAGE       = colors.HexColor("#4a6741")
GOLD       = colors.HexColor("#c9a227")
MUTED      = colors.HexColor("#7a7060")
BORDER     = colors.HexColor("#d4cfc3")
WHITE      = colors.white

SEVERITY_COLORS = {
    "critical": colors.HexColor("#c84b2f"),
    "high":     colors.HexColor("#e8623f"),
    "medium":   colors.HexColor("#c9a227"),
    "low":      colors.HexColor("#4a6741"),
}

GRADE_COLORS = {
    "A":  colors.HexColor("#4a6741"),
    "B+": colors.HexColor("#6a9a60"),
    "B":  colors.HexColor("#7aa2f7"),
    "C":  colors.HexColor("#c9a227"),
    "C-": colors.HexColor("#e8623f"),
    "D":  colors.HexColor("#c84b2f"),
    "D+": colors.HexColor("#c84b2f"),
    "F":  colors.HexColor("#8b0000"),
}


# ── Sample audit data (used when no JSON provided) ────────────
SAMPLE_AUDIT = {
    "domain": "knobillaesthetics.com",
    "business_name": "Knobill Aesthetics",
    "audit_date": datetime.now().strftime("%B %d, %Y"),
    "consultant": "AuditAI",
    "overall_score": 64,
    "overall_grade": "C-",
    "scores": {
        "SEO Health":    {"score": 58, "grade": "D+"},
        "Brand Trust":   {"score": 71, "grade": "B-"},
        "Conversion":    {"score": 44, "grade": "D"},
        "Technical":     {"score": 82, "grade": "B"},
    },
    "executive_summary": (
        "Knobill Aesthetics has a functional web presence with solid technical "
        "infrastructure, but is leaving significant revenue on the table due to "
        "conversion friction, pricing inconsistencies, and weak local SEO signals. "
        "The most urgent fix is correcting the Botox pricing discrepancy, which is "
        "actively eroding trust at the decision moment. With focused attention on "
        "quick wins, this site could realistically improve its overall score by "
        "15–20 points within 60 days."
    ),
    "critical_findings": [
        {
            "severity": "critical",
            "category": "Content / Trust",
            "title": "Pricing Inconsistency — Botox",
            "description": (
                "Botox is listed at $1,400 on /services but $1,500 on /pricing. "
                "When a prospect sees two different prices, they assume the higher "
                "one and abandon — or lose trust entirely."
            ),
            "impact": "Estimated 10–20% conversion loss at decision stage",
        },
        {
            "severity": "high",
            "category": "Technical SEO",
            "title": "Missing LocalBusiness Schema Markup",
            "description": (
                "No JSON-LD LocalBusiness schema detected on any page. Without this, "
                "Google cannot confidently surface the business in local pack results "
                "for '[service] near me' queries."
            ),
            "impact": "Invisible in local pack searches — primary competitor has it",
        },
        {
            "severity": "high",
            "category": "Conversion",
            "title": "No Booking CTA Above the Fold on Homepage",
            "description": (
                "The homepage hero section contains no call-to-action button. Visitors "
                "must scroll 800px before encountering any booking option. On mobile, "
                "this CTA is entirely absent."
            ),
            "impact": "Industry benchmark: above-fold CTA adds 15–30% more leads",
        },
        {
            "severity": "medium",
            "category": "Local SEO",
            "title": "Only 18 Google Reviews — Below Competitive Threshold",
            "description": (
                "The nearest competitor has 214 Google reviews with a 4.9 average. "
                "18 reviews signals a new or low-trust business regardless of "
                "actual quality."
            ),
            "impact": "Local pack ranking suppressed; lower click-through vs. competitors",
        },
        {
            "severity": "medium",
            "category": "Content",
            "title": "Service Pages Lead with Features, Not Outcomes",
            "description": (
                "Every service page opens with a clinical description of the procedure. "
                "High-converting service pages lead with the transformation the client "
                "will experience, then explain the process."
            ),
            "impact": "Reduced emotional resonance; lower time-on-page and conversions",
        },
    ],
    "action_plan": {
        "quick_wins": [
            {"task": "Fix Botox pricing inconsistency across /services and /pricing", "time": "1 hour", "owner": "Client"},
            {"task": "Add booking CTA button above the fold on homepage", "time": "2 hours", "owner": "Consultant"},
            {"task": "Install LocalBusiness JSON-LD schema on all pages", "time": "2 hours", "owner": "Consultant"},
            {"task": "Add click-to-call phone number to mobile header", "time": "1 hour", "owner": "Consultant"},
            {"task": "Optimize Google Business Profile (photos, services, description)", "time": "3 hours", "owner": "Client"},
        ],
        "medium_term": [
            {"task": "Rewrite homepage hero copy to lead with client transformation", "time": "1 week", "owner": "Consultant"},
            {"task": "Launch review generation campaign (SMS follow-up after appointments)", "time": "2 weeks", "owner": "Both"},
            {"task": "Create location-specific landing pages for target neighborhoods", "time": "3 weeks", "owner": "Consultant"},
            {"task": "Reduce booking form from 8 fields to 4 fields", "time": "2 hours", "owner": "Consultant"},
        ],
        "strategic": [
            {"task": "Develop before/after content library for top 5 services", "time": "Ongoing", "owner": "Client"},
            {"task": "Build FAQ schema content targeting 'near me' queries", "time": "1 month", "owner": "Consultant"},
            {"task": "Launch Google Ads campaign using audit data for targeting", "time": "2 weeks setup", "owner": "Consultant"},
            {"task": "Competitive repositioning: own the 'most transparent pricing' angle", "time": "Ongoing", "owner": "Both"},
        ],
    },
    "competitors": [
        {"tier": "Direct", "name": "Glow Aesthetics LA",     "url": "glowaesthetics.com",    "reviews": 214, "threat": "HIGH"},
        {"tier": "Direct", "name": "Beverly Skin Studio",    "url": "beverlyskin.com",        "reviews": 89,  "threat": "HIGH"},
        {"tier": "Indirect","name": "DermaFit Med Spa",      "url": "dermafitmedspa.com",     "reviews": 156, "threat": "MED"},
        {"tier": "Aspirational","name": "Skin Laundry",      "url": "skinlaundry.com",        "reviews": 1200,"threat": "N/A"},
    ],
}


# ── Style Definitions ─────────────────────────────────────────
def build_styles():
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=36,
            textColor=PAPER, leading=42, spaceAfter=8,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", parent=base["Normal"],
            fontName="Helvetica", fontSize=14,
            textColor=colors.HexColor("#aaa"), leading=20,
        ),
        "cover_grade": ParagraphStyle(
            "cover_grade", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=72,
            textColor=RUST, leading=80, alignment=TA_CENTER,
        ),
        "section_label": ParagraphStyle(
            "section_label", parent=base["Normal"],
            fontName="Helvetica", fontSize=8,
            textColor=MUTED, leading=12, spaceAfter=4,
            spaceBefore=20, letterSpacing=2,
        ),
        "section_heading": ParagraphStyle(
            "section_heading", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=22,
            textColor=INK, leading=28, spaceAfter=12,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontName="Helvetica", fontSize=10,
            textColor=INK, leading=16, spaceAfter=8,
        ),
        "body_muted": ParagraphStyle(
            "body_muted", parent=base["Normal"],
            fontName="Helvetica", fontSize=10,
            textColor=MUTED, leading=16, spaceAfter=8,
        ),
        "finding_title": ParagraphStyle(
            "finding_title", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=11,
            textColor=INK, leading=15, spaceAfter=4,
        ),
        "finding_cat": ParagraphStyle(
            "finding_cat", parent=base["Normal"],
            fontName="Helvetica", fontSize=8,
            textColor=MUTED, leading=12, letterSpacing=1,
        ),
        "finding_body": ParagraphStyle(
            "finding_body", parent=base["Normal"],
            fontName="Helvetica", fontSize=9.5,
            textColor=INK, leading=15, spaceAfter=4,
        ),
        "task": ParagraphStyle(
            "task", parent=base["Normal"],
            fontName="Helvetica", fontSize=10,
            textColor=INK, leading=15, leftIndent=12,
        ),
        "task_meta": ParagraphStyle(
            "task_meta", parent=base["Normal"],
            fontName="Helvetica", fontSize=8,
            textColor=MUTED, leading=12, leftIndent=12, spaceAfter=8,
        ),
        "table_header": ParagraphStyle(
            "table_header", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=8,
            textColor=PAPER, leading=12, alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "table_cell", parent=base["Normal"],
            fontName="Helvetica", fontSize=9,
            textColor=INK, leading=13, alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontName="Helvetica", fontSize=8,
            textColor=MUTED, leading=12, alignment=TA_CENTER,
        ),
    }


# ── Page Templates ────────────────────────────────────────────
def add_header_footer(canvas, doc, data):
    """Draw subtle header/footer on every non-cover page."""
    canvas.saveState()
    w, h = letter

    if doc.page > 1:
        # Header rule
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(0.65 * inch, h - 0.6 * inch, w - 0.65 * inch, h - 0.6 * inch)

        # Header text
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(0.65 * inch, h - 0.48 * inch, "AUDITAI MARKETING AUDIT REPORT")
        canvas.drawRightString(w - 0.65 * inch, h - 0.48 * inch, data["domain"].upper())

        # Footer rule
        canvas.line(0.65 * inch, 0.65 * inch, w - 0.65 * inch, 0.65 * inch)
        canvas.drawString(0.65 * inch, 0.45 * inch, f"Prepared {data['audit_date']} · Confidential")
        canvas.drawRightString(w - 0.65 * inch, 0.45 * inch, f"Page {doc.page}")

    canvas.restoreState()


# ── Score Bar Helper ─────────────────────────────────────────
def score_bar_table(label, score, grade, styles):
    """Returns a list of flowables rendering a labeled score bar."""
    bar_width = 4.5 * inch
    fill_w    = bar_width * (score / 100)
    grade_col = GRADE_COLORS.get(grade, MUTED)

    # Table: [label | bar (drawn via nested table) | grade | score]
    bar_bg   = Table([[""]], colWidths=[bar_width], rowHeights=[10])
    bar_bg.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), CREAM), ("BOX", (0,0), (-1,-1), 0.5, BORDER)]))

    bar_fill = Table([[""]], colWidths=[fill_w], rowHeights=[10])
    bar_fill.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), RUST)]))

    bar_stack = Table([[bar_bg]], colWidths=[bar_width], rowHeights=[12])

    row = Table(
        [[
            Paragraph(label, ParagraphStyle("bl", fontName="Helvetica", fontSize=10, textColor=INK)),
            bar_bg,
            Paragraph(f"<b>{grade}</b>", ParagraphStyle("gr", fontName="Helvetica-Bold", fontSize=12, textColor=grade_col, alignment=TA_CENTER)),
            Paragraph(f"{score}/100", ParagraphStyle("sc", fontName="Helvetica", fontSize=9, textColor=MUTED, alignment=TA_RIGHT)),
        ]],
        colWidths=[1.5*inch, bar_width, 0.6*inch, 0.8*inch],
        rowHeights=[20],
    )
    row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    return row


# ── Page Builders ─────────────────────────────────────────────

def page_cover(data, styles):
    story = []

    grade_col = GRADE_COLORS.get(data["overall_grade"], RUST)

    # Normalize business name to single clean line
    raw_name     = data.get("business_name", data["domain"])
    display_name = raw_name if len(raw_name) <= 32 else raw_name[:30] + "..."

    # ── Top rule ──────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=2, color=INK, spaceAfter=8))

    # ── Header strip: AuditAI | domain · date · confidential | section ──
    header_strip = Table([[
        Paragraph("<b>AUDITAI</b>", ParagraphStyle(
            "cvbrand", fontName="Helvetica-Bold", fontSize=9,
            textColor=INK, letterSpacing=2,
        )),
        Paragraph(
            f"{data['domain'].upper()} · {data['audit_date'].upper()} · CONFIDENTIAL",
            ParagraphStyle(
                "cvmeta", fontName="Helvetica", fontSize=8,
                textColor=MUTED, letterSpacing=1, alignment=TA_CENTER,
            ),
        ),
        Paragraph("SECTION 1 OF 6", ParagraphStyle(
            "cvsec", fontName="Helvetica", fontSize=8,
            textColor=MUTED, letterSpacing=1, alignment=TA_RIGHT,
        )),
    ]], colWidths=[2.0 * inch, 4.5 * inch, 1.5 * inch])
    header_strip.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), PAPER),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(header_strip)
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=48))

    # ── Grade + Business name block (light theme) ─────────────
    right_inner = Table([
        [Paragraph("AUDIT SUBJECT", ParagraphStyle(
            "aslbl2", fontName="Helvetica", fontSize=7.5,
            textColor=MUTED, letterSpacing=2, spaceAfter=6,
        ))],
        [Paragraph(display_name, ParagraphStyle(
            "bname2", fontName="Helvetica-Bold", fontSize=26,
            textColor=INK, leading=30, spaceAfter=4,
        ))],
        [Paragraph(data["domain"], ParagraphStyle(
            "dom2", fontName="Helvetica", fontSize=10,
            textColor=MUTED, leading=14,
        ))],
        [Spacer(1, 20)],
        [Paragraph(f"{data['overall_score']} / 100", ParagraphStyle(
            "oscore2", fontName="Helvetica-Bold", fontSize=34,
            textColor=grade_col, leading=38,
        ))],
        [Paragraph("OVERALL SCORE", ParagraphStyle(
            "oslbl2", fontName="Helvetica", fontSize=7.5,
            textColor=MUTED, letterSpacing=2,
        ))],
    ], colWidths=[4.6 * inch])
    right_inner.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))

    hero = Table([[
        Paragraph(data["overall_grade"], ParagraphStyle(
            "hgrade2", fontName="Helvetica-Bold", fontSize=80,
            textColor=grade_col, alignment=TA_CENTER, leading=88,
        )),
        right_inner,
    ]], colWidths=[2.8 * inch, 4.6 * inch])
    hero.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), PAPER),
        ("TOPPADDING",    (0, 0), (-1, -1), 20),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
        ("LEFTPADDING",   (0, 0), (0, -1),  0),
        ("RIGHTPADDING",  (0, 0), (0, -1),  0),
        ("LEFTPADDING",   (1, 0), (1, -1),  28),
        ("RIGHTPADDING",  (1, 0), (1, -1),  0),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LINEAFTER",     (0, 0), (0, -1),  0.5, BORDER),
    ]))
    story.append(hero)
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=36, spaceAfter=24))

    # ── Metadata strip: 4 cells ───────────────────────────────
    meta_labels = [
        Paragraph("DATE",        ParagraphStyle("ml2", fontName="Helvetica", fontSize=7, textColor=MUTED, letterSpacing=1.5, spaceAfter=3)),
        Paragraph("PREPARED BY", ParagraphStyle("ml2", fontName="Helvetica", fontSize=7, textColor=MUTED, letterSpacing=1.5, spaceAfter=3)),
        Paragraph("AGENTS",      ParagraphStyle("ml2", fontName="Helvetica", fontSize=7, textColor=MUTED, letterSpacing=1.5, spaceAfter=3)),
        Paragraph("STATUS",      ParagraphStyle("ml2", fontName="Helvetica", fontSize=7, textColor=MUTED, letterSpacing=1.5, spaceAfter=3)),
    ]
    meta_values = [
        Paragraph(data["audit_date"],       ParagraphStyle("mv2", fontName="Helvetica-Bold", fontSize=9, textColor=INK, leading=12)),
        Paragraph("AuditAI",                ParagraphStyle("mv2", fontName="Helvetica-Bold", fontSize=9, textColor=INK, leading=12)),
        Paragraph("6 Parallel Specialists", ParagraphStyle("mv2", fontName="Helvetica-Bold", fontSize=9, textColor=INK, leading=12)),
        Paragraph("Confidential",           ParagraphStyle("mv2", fontName="Helvetica-Bold", fontSize=9, textColor=INK, leading=12)),
    ]
    meta = Table(
        [meta_labels, meta_values],
        colWidths=[1.875 * inch] * 4,
    )
    meta.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), CREAM),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
        ("LINEAFTER",     (0, 0), (2, -1),  0.5, BORDER),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(meta)
    story.append(Spacer(1, 0.4 * inch))

    # ── Disclaimer ────────────────────────────────────────────
    story.append(Paragraph(
        "This report was generated by AuditAI using 6 parallel specialist agents. "
        "Findings reflect a point-in-time analysis and should be reviewed alongside "
        "live analytics data before implementation.",
        styles["body_muted"],
    ))
    story.append(PageBreak())
    return story

    # ── Hero: Grade left | Business details right ────────────
    right_inner = Table([
        [Paragraph("AUDIT SUBJECT", ParagraphStyle(
            "aslbl", fontName="Helvetica", fontSize=7.5,
            textColor=colors.HexColor("#888888"), letterSpacing=2, spaceAfter=4,
        ))],
        [Paragraph(display_name, ParagraphStyle(
            "bname", fontName="Helvetica-Bold", fontSize=22,
            textColor=PAPER, leading=26, spaceAfter=4,
        ))],
        [Paragraph(data["domain"], ParagraphStyle(
            "dom", fontName="Helvetica", fontSize=10,
            textColor=colors.HexColor("#aaaaaa"), leading=14,
        ))],
        [Spacer(1, 18)],
        [Paragraph(f"{data['overall_score']} / 100", ParagraphStyle(
            "oscore", fontName="Helvetica-Bold", fontSize=34,
            textColor=grade_col, leading=38,
        ))],
        [Paragraph("OVERALL SCORE", ParagraphStyle(
            "oslbl", fontName="Helvetica", fontSize=7.5,
            textColor=colors.HexColor("#888888"), letterSpacing=2,
        ))],
    ], colWidths=[4.6 * inch])
    right_inner.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))

    hero = Table([[
        Paragraph(data["overall_grade"], ParagraphStyle(
            "hgrade", fontName="Helvetica-Bold", fontSize=80,
            textColor=grade_col, alignment=TA_CENTER, leading=88,
        )),
        right_inner,
    ]], colWidths=[2.8 * inch, 4.6 * inch])
    hero.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), INK),
        ("TOPPADDING",    (0, 0), (-1, -1), 36),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 36),
        ("LEFTPADDING",   (0, 0), (0, -1),  24),
        ("RIGHTPADDING",  (0, 0), (0, -1),  0),
        ("LEFTPADDING",   (1, 0), (1, -1),  28),
        ("RIGHTPADDING",  (1, 0), (1, -1),  28),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LINEAFTER",     (0, 0), (0, -1),  0.5, colors.HexColor("#333333")),
    ]))
    story.append(hero)

    # ── Metadata strip ────────────────────────────────────────
    meta_labels = [
        Paragraph("DATE",        ParagraphStyle("ml", fontName="Helvetica", fontSize=7, textColor=colors.HexColor("#888888"), letterSpacing=1.5, spaceAfter=3)),
        Paragraph("PREPARED BY", ParagraphStyle("ml", fontName="Helvetica", fontSize=7, textColor=colors.HexColor("#888888"), letterSpacing=1.5, spaceAfter=3)),
        Paragraph("AGENTS",      ParagraphStyle("ml", fontName="Helvetica", fontSize=7, textColor=colors.HexColor("#888888"), letterSpacing=1.5, spaceAfter=3)),
        Paragraph("STATUS",      ParagraphStyle("ml", fontName="Helvetica", fontSize=7, textColor=colors.HexColor("#888888"), letterSpacing=1.5, spaceAfter=3)),
    ]
    meta_values = [
        Paragraph(data["audit_date"],       ParagraphStyle("mv", fontName="Helvetica-Bold", fontSize=9, textColor=INK, leading=12)),
        Paragraph("AuditAI",                ParagraphStyle("mv", fontName="Helvetica-Bold", fontSize=9, textColor=INK, leading=12)),
        Paragraph("6 Parallel Specialists", ParagraphStyle("mv", fontName="Helvetica-Bold", fontSize=9, textColor=INK, leading=12)),
        Paragraph("Confidential",           ParagraphStyle("mv", fontName="Helvetica-Bold", fontSize=9, textColor=INK, leading=12)),
    ]
    meta = Table(
        [meta_labels, meta_values],
        colWidths=[1.875 * inch] * 4,
    )
    meta.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), CREAM),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
        ("LINEAFTER",     (0, 0), (2, -1),  0.5, BORDER),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(meta)
    story.append(Spacer(1, 0.4 * inch))

    # ── Disclaimer ────────────────────────────────────────────
    story.append(Paragraph(
        "This report was generated by AuditAI using 6 parallel specialist agents. "
        "Findings reflect a point-in-time analysis and should be reviewed alongside "
        "live analytics data before implementation.",
        styles["body_muted"],
    ))
    story.append(PageBreak())
    return story


def page_executive_summary(data, styles):
    story = []
    story.append(Paragraph("EXECUTIVE SUMMARY", styles["section_label"]))
    story.append(Paragraph("What We Found", styles["section_heading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=16))
    story.append(Paragraph(data["executive_summary"], styles["body"]))
    story.append(Spacer(1, 0.3 * inch))

    # Top 3 critical findings callout
    story.append(Paragraph("TOP CRITICAL FINDINGS", styles["section_label"]))
    top3 = data["critical_findings"][:3]
    callout_data = [
        [Paragraph("PRIORITY", styles["table_header"]),
         Paragraph("FINDING", styles["table_header"]),
         Paragraph("IMPACT", styles["table_header"])],
    ]
    for i, f in enumerate(top3, 1):
        sev = f["severity"].upper()
        sev_col = SEVERITY_COLORS.get(f["severity"], MUTED)
        callout_data.append([
            Paragraph(f"<b>#{i} {sev}</b>", ParagraphStyle("sv", fontName="Helvetica-Bold", fontSize=9, textColor=sev_col, alignment=TA_CENTER)),
            Paragraph(f["title"], ParagraphStyle("ft", fontName="Helvetica", fontSize=9, textColor=INK)),
            Paragraph(f["impact"], ParagraphStyle("im", fontName="Helvetica", fontSize=8, textColor=MUTED)),
        ])

    callout = Table(callout_data, colWidths=[1.2*inch, 3.8*inch, 2.5*inch])
    callout.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  INK),
        ("BACKGROUND",    (0,1), (-1,-1), CREAM),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [PAPER, CREAM]),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("BOX",           (0,0), (-1,-1), 0.5, BORDER),
        ("LINEBELOW",     (0,0), (-1,0),  1, RUST),
        ("LINEBELOW",     (0,1), (-1,-2), 0.5, BORDER),
    ]))
    story.append(callout)
    story.append(PageBreak())
    return story


def page_scores(data, styles):
    story = []
    story.append(Paragraph("SCORE DASHBOARD", styles["section_label"]))
    story.append(Paragraph("Performance Breakdown", styles["section_heading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=20))

    for label, vals in data["scores"].items():
        story.append(score_bar_table(label, vals["score"], vals["grade"], styles))
        story.append(Spacer(1, 0.12 * inch))

    story.append(Spacer(1, 0.3 * inch))

    # Score interpretation
    story.append(Paragraph("SCORE INTERPRETATION", styles["section_label"]))
    interp_data = [
        [Paragraph("GRADE", styles["table_header"]), Paragraph("RANGE", styles["table_header"]), Paragraph("MEANING", styles["table_header"])],
        ["A",  "90–100", "Best-in-class — maintain and optimize"],
        ["B",  "80–89",  "Solid foundation — incremental gains available"],
        ["C",  "60–79",  "Functional but leaving revenue on the table"],
        ["D",  "50–59",  "Significant friction — urgent attention needed"],
        ["F",  "< 50",   "Critical issues actively costing revenue"],
    ]
    for row in interp_data[1:]:
        grade = row[0]
        row[0] = Paragraph(f"<b>{grade}</b>", ParagraphStyle("ig", fontName="Helvetica-Bold", fontSize=10, textColor=GRADE_COLORS.get(grade, MUTED), alignment=TA_CENTER))
        row[1] = Paragraph(row[1], ParagraphStyle("rg", fontName="Helvetica", fontSize=9, textColor=MUTED, alignment=TA_CENTER))
        row[2] = Paragraph(row[2], ParagraphStyle("mg", fontName="Helvetica", fontSize=9, textColor=INK))

    interp_table = Table(interp_data, colWidths=[0.8*inch, 1.2*inch, 5.5*inch])
    interp_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  INK),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [PAPER, CREAM]),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("BOX",           (0,0), (-1,-1), 0.5, BORDER),
        ("LINEBELOW",     (0,1), (-1,-2), 0.5, BORDER),
    ]))
    story.append(interp_table)
    story.append(PageBreak())
    return story


def page_findings(data, styles):
    story = []
    story.append(Paragraph("CRITICAL FINDINGS", styles["section_label"]))
    story.append(Paragraph("Issues Requiring Action", styles["section_heading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=20))

    for i, finding in enumerate(data["critical_findings"], 1):
        sev_col = SEVERITY_COLORS.get(finding["severity"], MUTED)
        severity_label = finding["severity"].upper()

        # Finding card using table
        card_content = [
            [
                Paragraph(f"<b>{severity_label}</b>", ParagraphStyle(
                    "sl", fontName="Helvetica-Bold", fontSize=8,
                    textColor=WHITE, alignment=TA_CENTER,
                )),
                Paragraph(f"<b>#{i} {finding['title']}</b>", styles["finding_title"]),
            ],
            [
                "",
                Paragraph(finding["category"].upper(), styles["finding_cat"]),
            ],
            [
                "",
                Paragraph(finding["description"], styles["finding_body"]),
            ],
            [
                "",
                Paragraph(f"<b>Impact:</b> {finding['impact']}", ParagraphStyle(
                    "im", fontName="Helvetica-Oblique", fontSize=9,
                    textColor=sev_col, leading=13,
                )),
            ],
        ]

        card = Table(card_content, colWidths=[0.9*inch, 6.6*inch])
        card.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (0,-1), sev_col),
            ("BACKGROUND",    (1,0), (1,-1), PAPER),
            ("BOX",           (0,0), (-1,-1), 0.5, BORDER),
            ("LINEAFTER",     (0,0), (0,-1), 1, BORDER),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("SPAN",          (0,0), (0,-1)),
            ("VALIGN",        (0,0), (0,-1), "MIDDLE"),
        ]))
        story.append(card)
        story.append(Spacer(1, 0.15 * inch))

    story.append(PageBreak())
    return story


def page_action_plan(data, styles):
    story = []
    story.append(Paragraph("PRIORITIZED ACTION PLAN", styles["section_label"]))
    story.append(Paragraph("Your 6-Month Roadmap", styles["section_heading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=16))

    sections = [
        ("QUICK WINS", "Week 1–4", SAGE,       data["action_plan"]["quick_wins"]),
        ("MEDIUM TERM","1–3 Months", GOLD,     data["action_plan"]["medium_term"]),
        ("STRATEGIC",  "3–6 Months", MUTED,    data["action_plan"]["strategic"]),
    ]

    for title, timeframe, col, tasks in sections:
        # Section header
        header = Table(
            [[
                Paragraph(f"<b>{title}</b>", ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=10, textColor=WHITE)),
                Paragraph(timeframe, ParagraphStyle("tf", fontName="Helvetica", fontSize=9, textColor=WHITE, alignment=TA_RIGHT)),
            ]],
            colWidths=[5 * inch, 2.5 * inch],
        )
        header.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), col),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING",   (0,0), (-1,-1), 14),
            ("RIGHTPADDING",  (0,0), (-1,-1), 14),
        ]))
        story.append(header)

        for task in tasks:
            row = Table(
                [[
                    Paragraph("☐", ParagraphStyle("cb", fontName="Helvetica", fontSize=12, textColor=col)),
                    Paragraph(task["task"], styles["task"]),
                    Paragraph(f"{task['time']} · {task['owner']}", styles["task_meta"]),
                ]],
                colWidths=[0.3*inch, 5.2*inch, 2.0*inch],
            )
            row.setStyle(TableStyle([
                ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                ("TOPPADDING",    (0,0), (-1,-1), 7),
                ("BOTTOMPADDING", (0,0), (-1,-1), 7),
                ("LEFTPADDING",   (0,0), (-1,-1), 10),
                ("LINEBELOW",     (0,0), (-1,-1), 0.5, BORDER),
                ("BACKGROUND",    (0,0), (-1,-1), PAPER),
            ]))
            story.append(row)

        story.append(Spacer(1, 0.2 * inch))

    story.append(PageBreak())
    return story


def page_competitors(data, styles):
    story = []
    story.append(Paragraph("COMPETITIVE LANDSCAPE", styles["section_label"]))
    story.append(Paragraph("3-Tier Competitor Analysis", styles["section_heading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=12))

    competitors = data.get("competitors", [])

    if not competitors:
        story.append(Paragraph("No competitor data available for this audit.", styles["body_muted"]))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("METHODOLOGY", styles["section_label"]))
        story.append(Paragraph(
            "This analysis was conducted using the AuditAI 5-agent framework: market-content, "
            "market-convert, market-compete, market-tech, and market-strategy. Agents run in "
            "parallel and cross-reference findings before final scoring. Scores are calculated "
            "using a weighted average (Technical 20%, SEO/Content 30%, Conversion 35%, "
            "Competitive 15%). Results reflect conditions at time of audit.",
            styles["body_muted"],
        ))
        return story

    tier_colors   = {"Direct": RUST, "Indirect": GOLD, "Aspirational": SAGE}
    threat_colors = {"HIGH": RUST,   "MED": GOLD,      "LOW": SAGE}

    name_style  = ParagraphStyle("cname",  fontName="Helvetica-Bold", fontSize=10,  textColor=INK,   leading=13)
    url_style   = ParagraphStyle("curl",   fontName="Helvetica",      fontSize=8,   textColor=MUTED, leading=11)
    badge_style = ParagraphStyle("cbadge", fontName="Helvetica-Bold", fontSize=7.5, textColor=WHITE, alignment=TA_CENTER, leading=10)
    lbl_style   = ParagraphStyle("clbl",   fontName="Helvetica-Bold", fontSize=8,   textColor=MUTED, leading=11, spaceBefore=6)
    val_style   = ParagraphStyle("cval",   fontName="Helvetica",      fontSize=8.5, textColor=INK,   leading=12)

    for c in competitors:
        tier        = c.get("tier",   "Direct")
        threat      = c.get("threat", "MED")
        tier_col    = tier_colors.get(tier,   MUTED)
        threat_col  = threat_colors.get(threat, MUTED)
        url_display = c.get("url","").replace("https://","").replace("http://","").replace("www.","").rstrip("/")

        # ── Left column: name, URL, tier badge, threat badge ──
        # Build as a single-column table so reportlab handles it as one Flowable
        left_rows = [
            [Paragraph(c["name"], name_style)],
            [Paragraph(url_display, url_style)],
            [Spacer(1, 6)],
            [Paragraph(f"  {tier.upper()}  ", badge_style)],
            [Spacer(1, 4)],
            [Paragraph(f"  THREAT: {threat}  ", badge_style)],
        ]
        left_inner = Table(left_rows, colWidths=[2.0*inch])
        left_inner.setStyle(TableStyle([
            ("BACKGROUND",    (0,3), (0,3), tier_col),
            ("BACKGROUND",    (0,5), (0,5), threat_col),
            ("TOPPADDING",    (0,0), (-1,-1), 2),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ]))

        # ── Right column: intelligence fields ──
        intel_fields = [
            ("Specialization",    c.get("specialization",  "")),
            ("Key Differentiator",c.get("differentiator",  "")),
            ("Serves",            c.get("serves",          "")),
            ("Geographic Reach",  c.get("reach",           "")),
            ("Weakness to Exploit",c.get("weakness",       "")),
        ]
        right_rows = []
        for label, val in intel_fields:
            if val:
                right_rows.append([Paragraph(label.upper(), lbl_style)])
                right_rows.append([Paragraph(val, val_style)])
        if not right_rows:
            right_rows = [[Paragraph("No additional data available.", val_style)]]

        right_inner = Table(right_rows, colWidths=[4.6*inch])
        right_inner.setStyle(TableStyle([
            ("TOPPADDING",    (0,0), (-1,-1), 1),
            ("BOTTOMPADDING", (0,0), (-1,-1), 1),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ]))

        # ── Outer card: left + right in one row ──
        card = Table(
            [[left_inner, right_inner]],
            colWidths=[2.2*inch, 4.7*inch],
        )
        card.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (0,0), PAPER),
            ("BACKGROUND",    (1,0), (1,0), WHITE),
            ("BOX",           (0,0), (-1,-1), 1.2, tier_col),
            ("LINEBEFORE",    (1,0), (1,-1), 0.5, BORDER),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("RIGHTPADDING",  (0,0), (-1,-1), 10),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ]))
        story.append(card)
        story.append(Spacer(1, 0.1*inch))

    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("METHODOLOGY", styles["section_label"]))
    story.append(Paragraph(
        "This analysis was conducted using the AuditAI 5-agent framework: market-content, "
        "market-convert, market-compete, market-tech, and market-strategy. Agents run in "
        "parallel and cross-reference findings before final scoring. Scores are calculated "
        "using a weighted average (Technical 20%, SEO/Content 30%, Conversion 35%, "
        "Competitive 15%). Results reflect conditions at time of audit.",
        styles["body_muted"],
    ))
    return story



# ── Main Generator ────────────────────────────────────────────

def generate_report(audit_data: dict, output_dir: str = "reports") -> str:
    os.makedirs(output_dir, exist_ok=True)
    domain_clean = audit_data["domain"].replace(".", "-").replace("/", "")
    date_str = datetime.now().strftime("%Y%m%d")
    filename = os.path.join(output_dir, f"{domain_clean}-audit-{date_str}.pdf")

    styles = build_styles()

    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.85 * inch,
        title=f"Marketing Audit — {audit_data['domain']}",
        author="AuditAI",
    )

    story = []
    story += page_cover(audit_data, styles)
    story += page_executive_summary(audit_data, styles)
    story += page_scores(audit_data, styles)
    story += page_findings(audit_data, styles)
    story += page_action_plan(audit_data, styles)
    story += page_competitors(audit_data, styles)

    doc.build(
        story,
        onFirstPage=lambda c, d: add_header_footer(c, d, audit_data),
        onLaterPages=lambda c, d: add_header_footer(c, d, audit_data),
    )

    print(f"\n✓ Report generated: {filename}")
    return filename


# ── CLI ───────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AuditAI PDF Report Generator")
    parser.add_argument("--domain", help="Domain to audit (uses sample data)", default=None)
    parser.add_argument("--json",   help="Path to audit JSON file", default=None)
    parser.add_argument("--output", help="Output directory", default="reports")
    args = parser.parse_args()

    if args.json:
        with open(args.json) as f:
            audit = json.load(f)
    else:
        audit = SAMPLE_AUDIT.copy()
        if args.domain:
            audit["domain"] = args.domain
            audit["business_name"] = args.domain.replace(".com", "").replace("-", " ").title()

    generate_report(audit, args.output)
