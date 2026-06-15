import uuid

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Dataset, Project, SafetyReport, SyntheticRun
from ..schemas import (
    ApprovalUpdate,
    GenerateRequest,
    PreviewOut,
    ReportOut,
    RunOut,
)
from ..services import exporters, generator, profiler, report, safety

router = APIRouter(prefix="/api", tags=["runs"])
settings = get_settings()


def _get_run(run_id: int, db: Session) -> SyntheticRun:
    run = db.get(SyntheticRun, run_id)
    if not run:
        raise HTTPException(404, "Synthetic run not found")
    return run


@router.post("/datasets/{dataset_id}/generate", response_model=RunOut)
def generate_synthetic(
    dataset_id: int,
    payload: GenerateRequest,
    db: Session = Depends(get_db),
) -> SyntheticRun:
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    source_df = profiler.read_csv(dataset.file_path)
    profile = dataset.profile_json

    synth_df = generator.generate(
        source_df,
        profile,
        row_count=payload.row_count,
        preserve_correlations=payload.preserve_correlations,
        add_noise=payload.add_noise,
        seed=payload.seed,
    )

    out_dir = settings.storage_dir / "synthetic"
    out_path = out_dir / f"{uuid.uuid4().hex}_synthetic.csv"
    synth_df.to_csv(out_path, index=False)

    run = SyntheticRun(
        project_id=dataset.project_id,
        dataset_id=dataset.id,
        mode="synthesize",
        generator_type="statistical",
        status="generated",
        row_count=int(len(synth_df)),
        settings_json=payload.model_dump(),
        file_path=str(out_path),
    )
    db.add(run)
    project = db.get(Project, dataset.project_id)
    if project:
        project.status = "generated"
    db.commit()
    db.refresh(run)
    return run


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: int, db: Session = Depends(get_db)) -> SyntheticRun:
    return _get_run(run_id, db)


@router.get("/runs/{run_id}/preview", response_model=PreviewOut)
def preview_run(run_id: int, limit: int = 100, db: Session = Depends(get_db)) -> PreviewOut:
    run = _get_run(run_id, db)
    df = pd.read_csv(run.file_path, nrows=limit)
    df = df.where(pd.notna(df), None)
    return PreviewOut(columns=list(df.columns), rows=df.to_dict(orient="records"))


@router.get("/runs/{run_id}/download")
def download_run(
    run_id: int, format: str = "csv", db: Session = Depends(get_db)
) -> StreamingResponse:
    run = _get_run(run_id, db)
    fmt = format.lower()
    if fmt not in {"csv", "pdf"}:
        raise HTTPException(400, "format must be 'csv' or 'pdf'")

    if fmt == "csv":
        def _iter():
            with open(run.file_path, "rb") as fh:
                yield from fh

        return StreamingResponse(
            _iter(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="synthetic_run_{run_id}.csv"'
            },
        )

    # PDF export
    df = pd.read_csv(run.file_path)
    pdf_bytes = exporters.dataframe_to_pdf_bytes(df, title=f"Synthetic Data - Run {run_id}")
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="synthetic_run_{run_id}.pdf"'
        },
    )


@router.post("/runs/{run_id}/report", response_model=ReportOut)
def build_report(run_id: int, db: Session = Depends(get_db)) -> SafetyReport:
    run = _get_run(run_id, db)
    dataset = db.get(Dataset, run.dataset_id) if run.dataset_id else None
    if not dataset:
        raise HTTPException(400, "Run has no source dataset to evaluate against")
    project = db.get(Project, run.project_id)

    real_df = profiler.read_csv(dataset.file_path)
    synth_df = pd.read_csv(run.file_path)
    profile = dataset.profile_json

    metrics = safety.evaluate(real_df, synth_df, profile)
    report_payload = report.generate_report(
        project={
            "name": project.name if project else "",
            "use_case": project.use_case if project else "",
            "industry": project.industry if project else "general",
        },
        profile=profile,
        metrics=metrics,
        run={"row_count": run.row_count, "generator_type": run.generator_type},
    )

    existing = run.report
    if existing:
        db.delete(existing)
        db.flush()

    report_row = SafetyReport(
        synthetic_run_id=run.id,
        privacy_score=metrics["privacy_score"],
        utility_score=metrics["utility_score"],
        risk_level=metrics["risk_level"],
        metrics_json=metrics,
        report_text=report_payload["report_text"],
        generated_by=report_payload["generated_by"],
        approved_status=report_payload["approved_status"],
    )
    db.add(report_row)
    run.status = "reviewed"
    db.commit()
    db.refresh(report_row)
    return report_row


@router.get("/runs/{run_id}/report", response_model=ReportOut)
def get_report(run_id: int, db: Session = Depends(get_db)) -> SafetyReport:
    run = _get_run(run_id, db)
    if not run.report:
        raise HTTPException(404, "No report yet. Generate one first.")
    return run.report


@router.get("/runs/{run_id}/report/download")
def download_report(run_id: int, db: Session = Depends(get_db)) -> PlainTextResponse:
    run = _get_run(run_id, db)
    if not run.report:
        raise HTTPException(404, "No report yet. Generate one first.")
    return PlainTextResponse(
        run.report.report_text,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="safety_report_run_{run_id}.md"'},
    )


@router.patch("/runs/{run_id}/approval", response_model=ReportOut)
def update_approval(
    run_id: int, payload: ApprovalUpdate, db: Session = Depends(get_db)
) -> SafetyReport:
    run = _get_run(run_id, db)
    if not run.report:
        raise HTTPException(404, "No report to approve. Generate one first.")
    allowed = {"needs_review", "approved", "rejected", "exported"}
    if payload.approved_status not in allowed:
        raise HTTPException(400, f"Status must be one of {sorted(allowed)}")
    run.report.approved_status = payload.approved_status
    if payload.approved_status == "approved":
        run.status = "approved"
    elif payload.approved_status == "rejected":
        run.status = "rejected"
    db.commit()
    db.refresh(run.report)
    return run.report
