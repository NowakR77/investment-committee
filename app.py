"""
Investment Committee Dashboard
Streamlit app for viewing investment memos and exporting them as PDFs.

Run with: streamlit run app.py
"""

import sys
from pathlib import Path

import streamlit as st

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
from export_report import convert_md_to_pdf

REPORTS_DIR = Path(__file__).resolve().parent / "reports"

st.set_page_config(
    page_title="Investment Committee",
    page_icon="📊",
    layout="wide",
)

st.title("Investment Committee Reports")

# Discover all markdown reports
md_files = sorted(REPORTS_DIR.glob("*.md"))

if not md_files:
    st.warning("No reports found in the /reports folder.")
    st.stop()

# Sidebar: report selector
report_names = {f.stem: f for f in md_files}
selected_name = st.sidebar.selectbox(
    "Select a report",
    options=list(report_names.keys()),
    format_func=lambda n: n.replace("_", " "),
)
selected_file = report_names[selected_name]

# Sidebar: PDF download
md_content = selected_file.read_text(encoding="utf-8")

pdf_bytes = convert_md_to_pdf(selected_file)
st.sidebar.download_button(
    label="Download PDF",
    data=pdf_bytes,
    file_name=f"{selected_name}.pdf",
    mime="application/pdf",
)

st.sidebar.markdown("---")
st.sidebar.caption(f"Reports found: {len(md_files)}")

# Main area: render the markdown
st.markdown(md_content, unsafe_allow_html=True)
