"""Statistical synthetic data generator.

Strategy per column (decided from the profile):
  * PII / sensitive (name, email, phone, ssn, address, dob)  -> regenerated
    with Faker so no real person survives.
  * id / high-cardinality strings -> format-preserving regeneration
    (keep the shape like "P-10023" but randomize the characters).
  * numeric  -> sampled from the empirical distribution; optionally tied
    together with a Gaussian copula to preserve correlations.
  * category / boolean -> sampled preserving observed frequencies.
  * datetime -> sampled uniformly within the observed range.
  * text     -> replaced with Faker sentences.

Original missing-value rates are reproduced per column.
"""

from __future__ import annotations

import random
import re
from typing import Any

import numpy as np
import pandas as pd
from faker import Faker
from scipy.stats import norm

_PII_FAKERS = {
    "name": lambda f: f.name(),
    "email": lambda f: f.email(),
    "phone": lambda f: f.phone_number(),
    "ssn": lambda f: f.ssn(),
    "address": lambda f: f.address().replace("\n", ", "),
    "dob": lambda f: f.date_of_birth(minimum_age=0, maximum_age=95).isoformat(),
    "medical": lambda f: f.bothify("DX-####"),
    "financial": lambda f: f.bothify("####-####-####-####"),
}


def _format_preserving(sample: str, rng: random.Random) -> str:
    out = []
    for ch in sample:
        if ch.isdigit():
            out.append(str(rng.randint(0, 9)))
        elif ch.isalpha():
            pool = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if ch.isupper() else "abcdefghijklmnopqrstuvwxyz"
            out.append(rng.choice(pool))
        else:
            out.append(ch)
    return "".join(out)


def _apply_missing(values: list[Any], missing_pct: float, rng: random.Random) -> list[Any]:
    if missing_pct <= 0:
        return values
    for i in range(len(values)):
        if rng.random() < missing_pct:
            values[i] = None
    return values


def _gen_numeric(series: pd.Series, n: int, stats: dict, add_noise: bool, rng: np.random.Generator) -> np.ndarray:
    source = pd.to_numeric(series, errors="coerce").dropna().to_numpy()
    if source.size == 0:
        return np.zeros(n)
    sampled = rng.choice(source, size=n, replace=True).astype(float)
    if add_noise and source.size > 1:
        std = float(np.std(source))
        if std > 0:
            # Larger jitter keeps synthetic values clearly distinct from any
            # single real record while staying within the observed range.
            sampled = sampled + rng.normal(0, std * 0.20, size=n)
    lo, hi = float(np.min(source)), float(np.max(source))
    sampled = np.clip(sampled, lo, hi)
    if stats.get("is_integer"):
        sampled = np.round(sampled)
    return sampled


def _gen_category(series: pd.Series, n: int, rng: np.random.Generator) -> np.ndarray:
    counts = series.dropna().astype(str).value_counts(normalize=True)
    if counts.empty:
        return np.array([""] * n, dtype=object)
    cats = counts.index.to_numpy()
    probs = counts.to_numpy()
    probs = probs / probs.sum()
    return rng.choice(cats, size=n, p=probs)


def _gen_datetime(series: pd.Series, n: int, rng: np.random.Generator) -> list[str]:
    parsed = pd.to_datetime(series, errors="coerce", format="mixed").dropna()
    if parsed.empty:
        return [""] * n
    lo = parsed.min().value
    hi = parsed.max().value
    if hi <= lo:
        return [parsed.min().isoformat()] * n
    picks = rng.integers(lo, hi, size=n)
    return [pd.Timestamp(int(p)).isoformat() for p in picks]


def _copula_numeric(
    df: pd.DataFrame, numeric_cols: list[str], n: int, profile_map: dict, rng: np.random.Generator
) -> dict[str, np.ndarray]:
    """Preserve correlations across numeric columns via a Gaussian copula."""
    clean = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    clean = clean.fillna(clean.mean())

    # Rank -> uniform -> standard normal scores.
    normal_scores = pd.DataFrame(index=clean.index)
    for col in numeric_cols:
        ranks = clean[col].rank(method="average")
        u = ranks / (len(clean) + 1)
        normal_scores[col] = norm.ppf(u.clip(1e-6, 1 - 1e-6))

    corr = np.corrcoef(normal_scores.to_numpy(), rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0)
    if corr.ndim == 0:
        corr = np.array([[1.0]])
    np.fill_diagonal(corr, 1.0)

    try:
        chol = np.linalg.cholesky(corr + np.eye(len(numeric_cols)) * 1e-6)
    except np.linalg.LinAlgError:
        chol = np.eye(len(numeric_cols))

    z = rng.standard_normal(size=(n, len(numeric_cols))) @ chol.T
    u = norm.cdf(z)

    result: dict[str, np.ndarray] = {}
    for j, col in enumerate(numeric_cols):
        source = pd.to_numeric(df[col], errors="coerce").dropna().to_numpy()
        if source.size == 0:
            result[col] = np.zeros(n)
            continue
        quantiles = np.quantile(source, u[:, j])
        stats = profile_map[col].get("stats", {})
        if stats.get("is_integer"):
            quantiles = np.round(quantiles)
        result[col] = quantiles
    return result


def generate(
    df: pd.DataFrame,
    profile: dict,
    row_count: int,
    preserve_correlations: bool = True,
    add_noise: bool = True,
    seed: int | None = None,
) -> pd.DataFrame:
    seed = seed if seed is not None else random.randint(1, 2**31 - 1)
    np_rng = np.random.default_rng(seed)
    py_rng = random.Random(seed)
    faker = Faker()
    Faker.seed(seed)

    profile_map = {c["name"]: c for c in profile["columns"]}
    numeric_cols = [
        c["name"]
        for c in profile["columns"]
        if c["logical_type"] == "numeric" and c["pii_kind"] not in ("id",)
    ]

    copula_data: dict[str, np.ndarray] = {}
    if preserve_correlations and len(numeric_cols) >= 2:
        copula_data = _copula_numeric(df, numeric_cols, row_count, profile_map, np_rng)

    out: dict[str, list[Any]] = {}
    for col in profile["columns"]:
        name = col["name"]
        kind = col["pii_kind"]
        logical = col["logical_type"]
        series = df[name] if name in df.columns else pd.Series(dtype=object)

        if kind in _PII_FAKERS:
            values: list[Any] = [_PII_FAKERS[kind](faker) for _ in range(row_count)]
        elif logical == "id" or (kind == "id"):
            samples = series.dropna().astype(str)
            template = samples.iloc[0] if not samples.empty else "ID-0000"
            values = [_format_preserving(template, py_rng) for _ in range(row_count)]
        elif logical == "numeric":
            if name in copula_data:
                values = list(copula_data[name])
            else:
                values = list(_gen_numeric(series, row_count, col.get("stats", {}), add_noise, np_rng))
        elif logical in ("category", "boolean"):
            values = list(_gen_category(series, row_count, np_rng))
        elif logical == "datetime":
            values = _gen_datetime(series, row_count, np_rng)
        elif logical == "text":
            values = [faker.sentence(nb_words=8) for _ in range(row_count)]
        else:
            values = list(_gen_category(series, row_count, np_rng))

        values = _apply_missing(values, col.get("missing_pct", 0.0), py_rng)
        out[name] = values

    result = pd.DataFrame(out, columns=[c["name"] for c in profile["columns"]])
    return result
