"""
Render the Clinical & Causal Evaluation Report (Markdown) to a polished,
circulation-ready PDF using ReportLab Platypus.

Handles the Markdown subset the report actually uses: H1-H3, paragraphs with
**bold**/*italic*/`code`, pipe tables, `> ` callout boxes, bullet/numbered
lists, and horizontal rules. Uses DejaVu Sans (full Unicode) when available so
glyphs like -, >=, ~ render correctly, falling back to Helvetica otherwise.
"""
from __future__ import annotations
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

# --- palette --------------------------------------------------------------- #
NAVY = colors.HexColor("#1F3A5F")
SLATE = colors.HexColor("#334155")
LIGHT = colors.HexColor("#F1F5F9")
BORDER = colors.HexColor("#CBD5E1")
CRIT = colors.HexColor("#B91C1C")      # critical/warning callouts
CRIT_BG = colors.HexColor("#FEF2F2")
INFO = colors.HexColor("#0E7490")      # note/bottom-line callouts
INFO_BG = colors.HexColor("#ECFEFF")

def _dejavu_dirs() -> list[Path]:
    """Candidate directories holding DejaVu Sans TTFs, across OSes.

    matplotlib (a hard dependency) BUNDLES DejaVu Sans on every platform, so it
    is the most reliable cross-platform source; system font dirs are fallbacks.
    """
    dirs: list[Path] = []
    try:
        import matplotlib
        dirs.append(Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf")
    except Exception:
        pass
    dirs += [
        Path("/usr/share/fonts/truetype/dejavu"),               # Debian/Ubuntu
        Path("/usr/share/fonts/dejavu"),                        # Fedora/Arch
        Path("/opt/homebrew/share/fonts"),                      # macOS (brew)
        Path("/usr/local/share/fonts"),                         # macOS/BSD
        Path.home() / ".local" / "share" / "fonts",             # user fonts
    ]
    return dirs


def _register_fonts() -> tuple[str, str, str]:
    """Register DejaVu Sans (full Unicode) if findable on ANY platform; else
    fall back to ReportLab's built-in Helvetica. Never raises."""
    reg, bold, ital = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"
    variants = {
        "DejaVu": "DejaVuSans.ttf",
        "DejaVu-Bold": "DejaVuSans-Bold.ttf",
        "DejaVu-Oblique": "DejaVuSans-Oblique.ttf",
    }
    try:
        found = {}
        for name, fname in variants.items():
            for d in _dejavu_dirs():
                p = d / fname
                if p.is_file():
                    found[name] = str(p)
                    break
        if len(found) == len(variants):     # all three weights located
            for name, path in found.items():
                pdfmetrics.registerFont(TTFont(name, path))
            reg, bold, ital = "DejaVu", "DejaVu-Bold", "DejaVu-Oblique"
    except Exception:
        pass                                 # Helvetica fallback is always safe
    return reg, bold, ital


def _inline(text: str, code_font: str) -> str:
    """Markdown inline -> ReportLab mini-HTML."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"`([^`]+?)`", rf'<font face="{code_font}" size=9>\1</font>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)
    return text


def _callout_flowable(lines, styles, code_font):
    """A '> ' block rendered as a colored, bordered box."""
    body = " ".join(l.lstrip("> ").rstrip() for l in lines)
    upper = body.upper()
    if any(k in upper for k in ("CRITICAL", "WARNING")):
        fg, bg = CRIT, CRIT_BG
    else:
        fg, bg = INFO, INFO_BG
    p = Paragraph(_inline(body, code_font), styles["callout"])
    t = Table([[p]], colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 3, fg),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def _table_flowable(rows, styles, code_font):
    """Pipe-table rows (already split) -> styled Table."""
    cells = [[Paragraph(_inline(c, code_font), styles["th" if i == 0 else "td"])
              for c in row] for i, row in enumerate(rows)]
    ncol = len(rows[0])
    # first column a bit wider (estimator/metric names)
    w0 = 2.0 * inch
    rest = (6.5 * inch - w0) / max(ncol - 1, 1)
    t = Table(cells, colWidths=[w0] + [rest] * (ncol - 1), repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
    ]
    t.setStyle(TableStyle(style))
    return t


def _split_row(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def markdown_to_pdf(md_path: str, pdf_path: str = "CLINICAL_CAUSAL_EVALUATION_REPORT.pdf",
                    footer: str = "Confidential — Causal Evaluation") -> str:
    reg, bold, ital = _register_fonts()
    ss = getSampleStyleSheet()

    styles = {
        "h1": ParagraphStyle("h1", parent=ss["Title"], fontName=bold, fontSize=20,
                             textColor=NAVY, spaceAfter=4, leading=24),
        "h2": ParagraphStyle("h2", fontName=bold, fontSize=14, textColor=NAVY,
                             spaceBefore=14, spaceAfter=6, leading=17),
        "h3": ParagraphStyle("h3", fontName=bold, fontSize=11.5, textColor=SLATE,
                             spaceBefore=10, spaceAfter=4, leading=14),
        "body": ParagraphStyle("body", fontName=reg, fontSize=9.5, textColor=SLATE,
                               leading=14, spaceAfter=6, alignment=TA_LEFT),
        "meta": ParagraphStyle("meta", fontName=reg, fontSize=9, textColor=SLATE,
                               leading=13),
        "li": ParagraphStyle("li", fontName=reg, fontSize=9.5, textColor=SLATE,
                             leading=14, leftIndent=14, spaceAfter=4),
        "callout": ParagraphStyle("callout", fontName=reg, fontSize=9, textColor=SLATE,
                                  leading=13),
        "th": ParagraphStyle("th", fontName=bold, fontSize=9, textColor=colors.white,
                             leading=11),
        "td": ParagraphStyle("td", fontName=reg, fontSize=8.5, textColor=SLATE,
                             leading=11),
    }

    with open(md_path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    story: list = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()

        if not s:
            i += 1
            continue

        # tables: a header line followed by a |:---| separator
        if s.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            rows = [_split_row(s)]
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                rows.append(_split_row(lines[i].strip()))
                i += 1
            story.append(Spacer(1, 4))
            story.append(_table_flowable(rows, styles, code_font=reg))
            story.append(Spacer(1, 6))
            continue

        # callout blocks
        if s.startswith(">"):
            block = [s]
            i += 1
            while i < n and lines[i].strip().startswith(">"):
                block.append(lines[i].strip())
                i += 1
            story.append(Spacer(1, 2))
            story.append(_callout_flowable(block, styles, code_font=reg))
            story.append(Spacer(1, 6))
            continue

        # headings
        if s.startswith("# "):
            story.append(Paragraph(_inline(s[2:], reg), styles["h1"]))
            story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY,
                                    spaceBefore=4, spaceAfter=8))
        elif s.startswith("## "):
            story.append(Paragraph(_inline(s[3:], reg), styles["h2"]))
        elif s.startswith("### "):
            story.append(Paragraph(_inline(s[4:], reg), styles["h3"]))
        elif s == "---":
            story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER,
                                    spaceBefore=6, spaceAfter=6))
        elif re.match(r"^\d+\.\s", s):
            story.append(Paragraph(_inline(s, reg), styles["li"]))
        elif s.startswith("- "):
            story.append(Paragraph("•&nbsp;" + _inline(s[2:], reg), styles["li"]))
        elif s.startswith("**") and s.endswith("**") and s.count("**") == 2:
            story.append(Paragraph(_inline(s, reg), styles["meta"]))
        else:
            story.append(Paragraph(_inline(s, reg), styles["body"]))
        i += 1

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(reg, 7.5)
        canvas.setFillColor(colors.HexColor("#94A3B8"))
        canvas.drawString(0.75 * inch, 0.5 * inch, footer)
        canvas.drawRightString(7.75 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        pdf_path, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        title="Clinical & Causal Evaluation Report",
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return pdf_path


if __name__ == "__main__":
    import sys
    md = sys.argv[1] if len(sys.argv) > 1 else "CLINICAL_CAUSAL_EVALUATION_REPORT.md"
    out = markdown_to_pdf(md)
    print("wrote", out)
