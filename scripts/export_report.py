"""
Export Report: Converts Markdown investment memos to professional PDFs.

Usage:
    python scripts/export_report.py                    # Convert all .md files in /reports
    python scripts/export_report.py reports/NOW*.md    # Convert a specific file

The convert_md_to_pdf() function is also importable for use by the Streamlit dashboard.
"""

import io
import re
import sys
from pathlib import Path

from fpdf import FPDF

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

# Colors
DARK_BLUE = (26, 58, 92)
MED_BLUE = (44, 95, 138)
HEADER_BG = (26, 58, 92)
ROW_ALT = (247, 249, 251)
WHITE = (255, 255, 255)
BLACK = (34, 34, 34)
GRAY = (136, 136, 136)
LIGHT_GRAY = (200, 200, 200)
RULE_COLOR = (204, 204, 204)


class ReportPDF(FPDF):
    """Custom PDF with header/footer for Investment Committee reports."""

    def __init__(self, title=""):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.report_title = title
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 6, "Investment Committee  --  Confidential", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*LIGHT_GRAY)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}}", align="C")


def _parse_table(lines, start_idx):
    """Parse a Markdown table starting at start_idx. Returns (rows, header_row, end_idx)."""
    rows = []
    i = start_idx
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        # Skip separator row (|---|---|)
        if all(re.match(r"^[-:]+$", c) for c in cells):
            i += 1
            continue
        rows.append(cells)
        i += 1
    header = rows[0] if rows else []
    body = rows[1:] if len(rows) > 1 else rows
    return header, body, i


def _render_table(pdf, header, body):
    """Render a table to the PDF."""
    if not header and not body:
        return

    n_cols = len(header) if header else (len(body[0]) if body else 0)
    if n_cols == 0:
        return

    usable_w = pdf.w - pdf.l_margin - pdf.r_margin
    col_w = usable_w / n_cols

    # Header
    if header:
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(*HEADER_BG)
        pdf.set_text_color(*WHITE)
        for j, cell in enumerate(header):
            w = col_w
            pdf.cell(w, 7, cell[:60], border=1, fill=True, align="L")
        pdf.ln()

    # Body rows
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*BLACK)
    for row_idx, row in enumerate(body):
        if row_idx % 2 == 1:
            pdf.set_fill_color(*ROW_ALT)
            fill = True
        else:
            pdf.set_fill_color(*WHITE)
            fill = True
        for j, cell in enumerate(row):
            w = col_w
            txt = cell[:80]
            # Strip bold markers for display
            txt = re.sub(r"\*\*(.+?)\*\*", r"\1", txt)
            pdf.cell(w, 6, txt, border=1, fill=fill, align="L")
        pdf.ln()

    pdf.ln(3)


def _clean_inline(text):
    """Strip markdown inline formatting for plain-text output."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)        # italic
    text = re.sub(r"`(.+?)`", r"\1", text)          # code
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links
    # Replace unicode chars that Helvetica can't render
    text = text.replace("\u2014", "--")   # em dash
    text = text.replace("\u2013", "-")    # en dash
    text = text.replace("\u2018", "'")    # left single quote
    text = text.replace("\u2019", "'")    # right single quote
    text = text.replace("\u201c", '"')    # left double quote
    text = text.replace("\u201d", '"')    # right double quote
    text = text.replace("\u2022", "-")    # bullet
    text = text.replace("\u00a0", " ")    # non-breaking space
    text = text.replace("\u2026", "...")  # ellipsis
    text = text.replace("\u1f916", "")    # robot emoji
    # Catch any remaining non-latin1 characters
    text = text.encode("latin-1", errors="replace").decode("latin-1")
    return text.strip()


def convert_md_to_pdf(md_path):
    """Convert a Markdown file to PDF bytes.

    Args:
        md_path: Path to the .md file.

    Returns:
        PDF content as bytes.
    """
    md_path = Path(md_path)
    md_text = md_path.read_text(encoding="utf-8")
    lines = md_text.split("\n")

    pdf = ReportPDF(title=md_path.stem)
    pdf.alias_nb_pages()
    pdf.set_margins(left=15, top=15, right=15)
    pdf.add_page()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Blank line
        if not stripped:
            pdf.ln(2)
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^---+$", stripped):
            y = pdf.get_y()
            pdf.set_draw_color(*RULE_COLOR)
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(4)
            i += 1
            continue

        # H1
        if stripped.startswith("# ") and not stripped.startswith("## "):
            text = _clean_inline(stripped[2:])
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(*DARK_BLUE)
            pdf.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
            y = pdf.get_y()
            pdf.set_draw_color(*DARK_BLUE)
            pdf.set_line_width(0.6)
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.set_line_width(0.2)
            pdf.ln(4)
            i += 1
            continue

        # H2
        if stripped.startswith("## ") and not stripped.startswith("### "):
            text = _clean_inline(stripped[3:])
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(*DARK_BLUE)
            pdf.ln(4)
            pdf.cell(0, 9, text, new_x="LMARGIN", new_y="NEXT")
            y = pdf.get_y()
            pdf.set_draw_color(*LIGHT_GRAY)
            pdf.set_line_width(0.3)
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.set_line_width(0.2)
            pdf.ln(3)
            i += 1
            continue

        # H3
        if stripped.startswith("### "):
            text = _clean_inline(stripped[4:])
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*MED_BLUE)
            pdf.ln(2)
            pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            i += 1
            continue

        # Table
        if stripped.startswith("|"):
            header, body, end_idx = _parse_table(lines, i)
            _render_table(pdf, header, body)
            i = end_idx
            continue

        # Bullet points
        if re.match(r"^[-*]\s", stripped):
            text = _clean_inline(re.sub(r"^[-*]\s+", "", stripped))
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*BLACK)
            indent = 6
            pdf.set_x(pdf.l_margin)
            pdf.cell(indent, 5, " -")
            remaining_w = pdf.w - pdf.l_margin - pdf.r_margin - indent
            pdf.multi_cell(remaining_w, 5, text)
            i += 1
            continue

        # Numbered list
        m = re.match(r"^(\d+)\.\s+(.+)", stripped)
        if m:
            text = _clean_inline(m.group(2))
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*BLACK)
            indent = 8
            pdf.set_x(pdf.l_margin)
            pdf.cell(indent, 5, f" {m.group(1)}.")
            remaining_w = pdf.w - pdf.l_margin - pdf.r_margin - indent
            pdf.multi_cell(remaining_w, 5, text)
            i += 1
            continue

        # Regular paragraph
        text = _clean_inline(stripped)
        if text:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*BLACK)
            pdf.multi_cell(0, 5, text)
            pdf.ln(1)
        i += 1

    # Output to bytes
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def convert_md_to_pdf_file(md_path):
    """Convert a Markdown file to a PDF file saved alongside the source.

    Returns:
        Path to the generated PDF file.
    """
    md_path = Path(md_path)
    pdf_path = md_path.with_suffix(".pdf")
    pdf_bytes = convert_md_to_pdf(md_path)
    pdf_path.write_bytes(pdf_bytes)
    return pdf_path


def main():
    if len(sys.argv) > 1:
        md_files = [Path(p) for p in sys.argv[1:]]
    else:
        md_files = sorted(REPORTS_DIR.glob("*.md"))

    if not md_files:
        print("No .md files found in", REPORTS_DIR)
        sys.exit(1)

    print(f"Converting {len(md_files)} report(s) to PDF...\n")

    for md_file in md_files:
        try:
            pdf_path = convert_md_to_pdf_file(md_file)
            size_kb = pdf_path.stat().st_size / 1024
            print(f"  [OK] {md_file.name} -> {pdf_path.name} ({size_kb:.0f} KB)")
        except Exception as e:
            print(f"  [FAIL] {md_file.name}: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
