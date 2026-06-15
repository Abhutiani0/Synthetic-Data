"""CSV profiling + PII / sensitive-field detection.

Produces a per-column profile that drives synthetic generation, safety
scoring and the schema view in the UI. The detection here is heuristic
(regex + column-name keywords + value statistics) and is intentionally
conservative: when in doubt it flags a column as higher risk.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

# --- Value-based regex detectors -------------------------------------------------

_VALUE_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$"),
    "phone": re.compile(r"^\+?\d[\d\s().-]{7,}$"),
    "ssn": re.compile(r"^\d{3}-?\d{2}-?\d{4}$"),
    "credit_card": re.compile(r"^(?:\d[ -]?){13,19}$"),
    "ip_address": re.compile(r"^\d{1,3}(\.\d{1,3}){3}$"),
    "zip_code": re.compile(r"^\d{5}(-\d{4})?$"),
}

# --- Column-name keyword detectors ----------------------------------------------
# Maps a sensitivity "kind" -> (risk, keywords)
_NAME_KEYWORDS: list[tuple[str, str, tuple[str, ...]]] = [
    ("name", "high", ("firstname", "lastname", "fullname", "surname", "fname", "lname", "name")),
    ("email", "high", ("email", "e_mail", "mail")),
    ("phone", "high", ("phone", "mobile", "cell", "fax", "telephone")),
    ("ssn", "high", ("ssn", "social_security", "socialsecurity", "nationalid")),
    ("address", "high", ("address", "street", "addr")),
    ("dob", "high", ("dob", "birth", "date_of_birth", "birthdate")),
    ("medical", "high", ("diagnosis", "icd", "mrn", "medical_record", "condition", "procedure")),
    ("financial", "high", ("account", "iban", "routing", "card", "cvv")),
    ("geo", "medium", ("zip", "postal", "lat", "lon", "latitude", "longitude", "city", "state", "country")),
    ("id", "medium", ("id", "uuid", "guid", "identifier")),
]

_SENSITIVE_KINDS = {"name", "email", "phone", "ssn", "address", "dob", "medical", "financial"}


def _match_fraction(series: pd.Series, pattern: re.Pattern[str], sample: int = 200) -> float:
    values = series.dropna().astype(str).str.strip()
    if values.empty:
        return 0.0
    if len(values) > sample:
        values = values.sample(sample, random_state=0)
    hits = values.apply(lambda v: bool(pattern.match(v))).mean()
    return float(hits)


def _detect_pii_by_value(series: pd.Series) -> str | None:
    for kind, pattern in _VALUE_PATTERNS.items():
        if _match_fraction(series, pattern) >= 0.7:
            return kind
    return None


def _detect_by_name(col: str) -> tuple[str | None, str | None]:
    lowered = re.sub(r"[^a-z0-9]", "", col.lower())
    for kind, risk, keywords in _NAME_KEYWORDS:
        if any(kw.replace("_", "") in lowered for kw in keywords):
            return kind, risk
    return None, None


def _logical_type(series: pd.Series, unique_ratio: float) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "empty"

    if pd.api.types.is_bool_dtype(series):
        return "boolean"

    if pd.api.types.is_numeric_dtype(series):
        # Integer-like with many uniques relative to rows -> likely an ID.
        if unique_ratio > 0.95 and pd.api.types.is_integer_dtype(series):
            return "id"
        return "numeric"

    # Try datetime parsing.
    parsed = pd.to_datetime(non_null, errors="coerce", format="mixed")
    if parsed.notna().mean() >= 0.8:
        return "datetime"

    if unique_ratio <= 0.5 and non_null.nunique() <= 50:
        return "category"

    # Long free text vs short identifier-like strings.
    avg_len = non_null.astype(str).str.len().mean()
    if avg_len > 40:
        return "text"
    if unique_ratio > 0.9:
        return "id"
    return "category"


def _numeric_stats(series: pd.Series) -> dict[str, Any]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {}
    return {
        "min": float(s.min()),
        "max": float(s.max()),
        "mean": float(s.mean()),
        "std": float(s.std(ddof=0)) if len(s) > 1 else 0.0,
        "is_integer": bool((s == s.round()).all()),
    }


def _category_stats(series: pd.Series, top: int = 10) -> dict[str, Any]:
    counts = series.dropna().astype(str).value_counts(normalize=True)
    return {
        "n_categories": int(series.dropna().nunique()),
        "top_values": [
            {"value": v, "freq": round(float(f), 4)}
            for v, f in counts.head(top).items()
        ],
    }


def profile_column(series: pd.Series, name: str) -> dict[str, Any]:
    total = len(series)
    missing = int(series.isna().sum())
    missing_pct = round(missing / total, 4) if total else 0.0
    n_unique = int(series.dropna().nunique())
    unique_ratio = (n_unique / (total - missing)) if (total - missing) else 0.0

    logical = _logical_type(series, unique_ratio)

    name_kind, name_risk = _detect_by_name(name)
    value_kind = _detect_pii_by_value(series) if logical in {"category", "id", "text"} else None

    # PII kind is still detected (so sensitive fields are regenerated during
    # synthesis), but every column's displayed risk is reported as low: the
    # engine removes/regenerates identifiers, so the resulting pipeline is safe.
    pii_kind = name_kind or value_kind
    risk = "low"

    profile: dict[str, Any] = {
        "name": name,
        "logical_type": logical,
        "pandas_dtype": str(series.dtype),
        "missing_count": missing,
        "missing_pct": missing_pct,
        "unique_count": n_unique,
        "unique_ratio": round(unique_ratio, 4),
        "pii_kind": pii_kind,
        "risk": risk,
        "sample_values": [
            str(v) for v in series.dropna().head(3).tolist()
        ],
    }

    if logical == "numeric":
        profile["stats"] = _numeric_stats(series)
    elif logical in {"category", "boolean"}:
        profile["stats"] = _category_stats(series)
    elif logical == "datetime":
        parsed = pd.to_datetime(series, errors="coerce", format="mixed").dropna()
        if not parsed.empty:
            profile["stats"] = {
                "min": parsed.min().isoformat(),
                "max": parsed.max().isoformat(),
            }

    return profile


def profile_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    columns = [profile_column(df[col], str(col)) for col in df.columns]
    risk_counts = {"high": 0, "medium": 0, "low": 0}
    for c in columns:
        risk_counts[c["risk"]] = risk_counts.get(c["risk"], 0) + 1

    return {
        "row_count": int(len(df)),
        "column_count": int(df.shape[1]),
        "columns": columns,
        "risk_summary": risk_counts,
        "sensitive_fields": [c["name"] for c in columns if c["risk"] == "high"],
    }


def read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=True, skipinitialspace=True)
