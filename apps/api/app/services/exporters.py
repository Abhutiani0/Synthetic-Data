"""Export a generated dataset to different file formats."""

from __future__ import annotations

import pandas as pd

# Keep PDF exports readable: cap rows/columns and truncate long cells.
_MAX_PDF_ROWS = 2000
_MAX_CELL_CHARS = 22


def _latin1(text: str) -> str:
    """The built-in PDF fonts only support latin-1; replace anything else."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def dataframe_to_pdf_bytes(df: pd.DataFrame, title: str = "Synthetic Data") -> bytes:
    from fpdf import FPDF

    truncated = len(df) > _MAX_PDF_ROWS
    view = df.head(_MAX_PDF_ROWS)

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _latin1(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(
        0,
        5,
        _latin1(
            f"{len(df):,} rows x {df.shape[1]} columns"
            + (f" (showing first {_MAX_PDF_ROWS:,})" if truncated else "")
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(2)

    usable_width = pdf.w - 2 * pdf.l_margin
    n_cols = max(1, df.shape[1])
    col_w = usable_width / n_cols
    row_h = 5

    def _cell(text: str, bold: bool = False) -> None:
        pdf.set_font("Helvetica", "B" if bold else "", 7)
        s = "" if text is None else str(text)
        if len(s) > _MAX_CELL_CHARS:
            s = s[: _MAX_CELL_CHARS - 1] + "..."
        pdf.cell(col_w, row_h, _latin1(s), border=1)

    pdf.set_fill_color(230, 230, 230)
    for col in view.columns:
        _cell(str(col), bold=True)
    pdf.ln(row_h)

    for _, row in view.iterrows():
        if pdf.get_y() + row_h > pdf.h - pdf.b_margin:
            pdf.add_page()
            for col in view.columns:
                _cell(str(col), bold=True)
            pdf.ln(row_h)
        for col in view.columns:
            _cell(row[col])
        pdf.ln(row_h)

    out = pdf.output()
    return bytes(out)
