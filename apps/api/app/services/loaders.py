"""Load tabular data from an uploaded file (CSV or PDF).

PDFs are parsed with pdfplumber: we extract every table on every page and
stack the ones that share the widest, most consistent column count. The
first row of the chosen table is used as the header. PDF table extraction
is best-effort -- clean, grid-style tables work well; free-form documents
may not yield a usable table, in which case a clear error is raised.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=True, skipinitialspace=True)


def _read_pdf(path: str) -> pd.DataFrame:
    import pdfplumber

    tables: list[list[list[str]]] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if table and len(table) >= 2:
                    tables.append(table)

    if not tables:
        raise ValueError(
            "No tabular data could be extracted from this PDF. "
            "Please upload a PDF that contains a clear table, or use a CSV."
        )

    # Pick the most common column count, then stack matching tables.
    widths = [len(t[0]) for t in tables]
    target_width = max(set(widths), key=widths.count)
    matching = [t for t in tables if len(t[0]) == target_width]

    header = [
        (str(h).strip() if h is not None else f"col_{i}")
        for i, h in enumerate(matching[0][0])
    ]
    # De-duplicate / fill empty header names.
    seen: dict[str, int] = {}
    clean_header = []
    for i, h in enumerate(header):
        name = h or f"col_{i}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        clean_header.append(name)

    rows: list[list] = []
    for t in matching:
        for r in t[1:]:
            if len(r) == target_width:
                rows.append([(str(c).strip() if c is not None else None) for c in r])

    df = pd.DataFrame(rows, columns=clean_header)
    # Best-effort numeric coercion for columns that are mostly numbers.
    for col in df.columns:
        coerced = pd.to_numeric(df[col], errors="coerce")
        if coerced.notna().mean() >= 0.8:
            df[col] = coerced
    return df


def load_dataframe(path: str, filename: str) -> pd.DataFrame:
    ext = Path(filename).suffix.lower()
    if ext == ".csv":
        return _read_csv(path)
    if ext == ".pdf":
        return _read_pdf(path)
    raise ValueError("Unsupported file type. Upload a .csv or .pdf file.")


SUPPORTED_EXTENSIONS = {".csv", ".pdf"}
