"""Safety & utility report generation.

Default path is a fully deterministic Markdown report built from the
profile + safety metrics, so the product works with zero external
dependencies. If an OpenAI key is configured, a narrative summary is
generated from *only* the schema and aggregate statistics -- never raw
rows -- consistent with the privacy design.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def _check(passed: bool) -> str:
    return "Pass" if passed else "Needs review"


def _approval_recommendation(risk_level: str, utility_score: float) -> tuple[str, str]:
    if risk_level == "low" and utility_score >= 70:
        return (
            "approved",
            "Approved for internal testing, demos, and analytics. Review before "
            "external release or production model training.",
        )
    if risk_level == "medium":
        return (
            "needs_review",
            "Conditional. Suitable for internal testing/demos after a privacy "
            "reviewer confirms the similarity findings below are acceptable.",
        )
    return (
        "needs_review",
        "Not recommended for sharing yet. Re-generate with stronger privacy "
        "settings (more rows, more noise) and re-run the safety scan.",
    )


def build_markdown(
    project: dict[str, Any],
    profile: dict[str, Any],
    metrics: dict[str, Any],
    run: dict[str, Any],
    ai_narrative: str | None = None,
) -> str:
    privacy = metrics["privacy"]
    utility = metrics["utility"]
    rec_status, rec_text = _approval_recommendation(metrics["risk_level"], metrics["utility_score"])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    sensitive = profile.get("sensitive_fields", [])
    lines: list[str] = []
    a = lines.append

    a("# Synthetic Data Safety and Utility Report")
    a("")
    a(f"**Project:** {project.get('name', '')}  ")
    a(f"**Use Case:** {project.get('use_case') or 'Not specified'}  ")
    a(f"**Industry:** {project.get('industry', 'general')}  ")
    a(f"**Generated:** {now}  ")
    a(f"**Rows Generated:** {run.get('row_count', 0):,}  ")
    a(f"**Synthetic Method:** {run.get('generator_type', 'statistical')} pattern synthesis")
    a("")

    a("## 1. Headline Scores")
    a("")
    a("| Metric | Score |")
    a("| --- | --- |")
    a(f"| Privacy Score | **{metrics['privacy_score']}/100** |")
    a(f"| Trend Accuracy | **{metrics['utility_score']}/100** |")
    a(f"| Risk Level | **{metrics['risk_level'].upper()}** |")
    a("")

    if ai_narrative:
        a("## 2. Summary")
        a("")
        a(ai_narrative.strip())
        a("")

    a("## 3. Source Data Overview")
    a("")
    a(f"- Columns: {profile.get('column_count', 0)}")
    a(f"- Source rows: {profile.get('row_count', 0):,}")
    rs = profile.get("risk_summary", {})
    a(f"- Field risk breakdown: {rs.get('high', 0)} high, {rs.get('medium', 0)} medium, {rs.get('low', 0)} low")
    a("")

    a("## 4. Sensitive Field Detection")
    a("")
    if sensitive:
        a("| Field | Detected Type | Risk | Handling |")
        a("| --- | --- | --- | --- |")
        for col in profile["columns"]:
            if col["risk"] == "high":
                handling = "Regenerated (no real values retained)"
                a(f"| {col['name']} | {col.get('pii_kind') or col['logical_type']} | High | {handling} |")
    else:
        a("No high-risk direct identifiers were detected in the source data.")
    a("")

    a("## 5. Privacy Risk Analysis")
    a("")
    a("| Check | Result | Evidence |")
    a("| --- | --- | --- |")
    a(f"| PII removed | {_check(privacy['checks']['pii_removed'])} | leakage rate {_pct(privacy['pii_leak_rate'])} |")
    a(f"| Real-row duplication | {_check(privacy['checks']['no_duplicate_rows'])} | {privacy['duplicate_rows']} duplicate rows ({_pct(privacy['duplicate_rate'])}) |")
    a(f"| Similarity risk | {_check(privacy['checks']['low_similarity'])} | {_pct(privacy['too_similar_rate'])} of rows near a real record |")
    a("")
    a(
        "Re-identification is assessed with a nearest-neighbour distance over "
        "mixed-type fields (mean distance "
        f"{privacy['mean_nn_distance']}). This is the kind of quantitative "
        "evidence an Expert Determination (HIPAA) review expects, rather than "
        "an unsupported assertion of safety."
    )
    a("")

    a("## 6. Trend Accuracy Analysis")
    a("")
    a("| Metric | Score |")
    a("| --- | --- |")
    a(f"| Distribution similarity | {_pct(utility['distribution_similarity'])} |")
    a(f"| Correlation similarity | {_pct(utility['correlation_similarity'])} |")
    a(f"| Missing-value match | {_pct(utility['missing_value_match'])} |")
    a("")

    a("## 7. Bias and Fairness Notes")
    a("")
    a(
        "Category frequencies and missing-value patterns are preserved from the "
        "source, so any imbalance present in the original data will also be "
        "present here. Review category distributions before using this data to "
        "train or evaluate models."
    )
    a("")

    a("## 8. Recommended Use Cases")
    a("")
    a("- Software testing and QA without exposing real records")
    a("- Demo and staging environments")
    a("- Dashboard and analytics prototyping")
    a("")

    a("## 9. Restrictions")
    a("")
    a("- This dataset is synthetic and must not be treated as real data.")
    a("- Do not use for clinical, financial, or other real-world decisions.")
    a("- Review before external release, public sharing, or production model training.")
    a("")

    a("## 10. Approval Decision")
    a("")
    a(f"**Recommendation:** {rec_text}")
    a("")
    a(f"_Suggested status: `{rec_status}` — requires human reviewer confirmation._")
    a("")

    return "\n".join(lines)


def _build_ai_narrative(project, profile, metrics, run) -> str | None:
    from ..config import get_settings

    settings = get_settings()
    if not settings.ai_enabled:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    # Build a privacy-safe context: schema + aggregate stats only. No raw rows.
    schema = [
        {
            "name": c["name"],
            "type": c["logical_type"],
            "risk": c["risk"],
            "missing_pct": c["missing_pct"],
        }
        for c in profile["columns"]
    ]
    context = {
        "project": {"name": project.get("name"), "use_case": project.get("use_case"), "industry": project.get("industry")},
        "rows_generated": run.get("row_count"),
        "schema": schema,
        "privacy_score": metrics["privacy_score"],
        "utility_score": metrics["utility_score"],
        "risk_level": metrics["risk_level"],
        "privacy_metrics": metrics["privacy"],
        "utility_metrics": metrics["utility"],
    }

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a privacy and data-governance analyst. Using ONLY the "
                        "provided schema and aggregate metrics (you have NO access to raw "
                        "rows), write a concise, factual 2-3 paragraph summary of the "
                        "privacy posture and utility of a synthetic dataset. Be measured: "
                        "cite the metrics, avoid claiming guarantees, and note limitations."
                    ),
                },
                {"role": "user", "content": str(context)},
            ],
        )
        return resp.choices[0].message.content
    except Exception:
        return None


def generate_report(
    project: dict[str, Any],
    profile: dict[str, Any],
    metrics: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    ai_narrative = _build_ai_narrative(project, profile, metrics, run)
    generated_by = "openai" if ai_narrative else "local"
    markdown = build_markdown(project, profile, metrics, run, ai_narrative)
    rec_status, _ = _approval_recommendation(metrics["risk_level"], metrics["utility_score"])
    return {
        "report_text": markdown,
        "generated_by": generated_by,
        "approved_status": rec_status,
    }
