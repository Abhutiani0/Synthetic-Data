import uuid
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Dataset, Project
from ..schemas import DatasetOut
from ..services import loaders, profiler

router = APIRouter(prefix="/api", tags=["datasets"])
settings = get_settings()


@router.post("/projects/{project_id}/datasets", response_model=DatasetOut)
async def upload_dataset(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Dataset:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in loaders.SUPPORTED_EXTENSIONS:
        raise HTTPException(400, "Only .csv and .pdf files are supported")

    upload_dir = settings.storage_dir / "uploads"
    safe_name = f"{uuid.uuid4().hex}_{Path(file.filename).name}"
    raw_path = upload_dir / safe_name
    content = await file.read()
    raw_path.write_bytes(content)

    try:
        df = loaders.load_dataframe(str(raw_path), file.filename)
    except Exception as exc:  # noqa: BLE001
        raw_path.unlink(missing_ok=True)
        raise HTTPException(400, f"Could not parse file: {exc}") from exc

    if df.empty:
        raw_path.unlink(missing_ok=True)
        raise HTTPException(400, "The uploaded file has no rows")

    # Normalize to CSV so downstream generation/scoring is format-agnostic.
    normalized_path = upload_dir / f"{uuid.uuid4().hex}_normalized.csv"
    df.to_csv(normalized_path, index=False)

    profile = profiler.profile_dataframe(df)

    dataset = Dataset(
        project_id=project_id,
        filename=file.filename,
        file_path=str(normalized_path),
        row_count=profile["row_count"],
        column_count=profile["column_count"],
        profile_json=profile,
    )
    db.add(dataset)
    if project.status == "draft":
        project.status = "profiled"
    db.commit()
    db.refresh(dataset)
    return dataset


@router.get("/projects/{project_id}/datasets", response_model=list[DatasetOut])
def list_datasets(project_id: int, db: Session = Depends(get_db)) -> list[Dataset]:
    return list(
        db.scalars(
            select(Dataset)
            .where(Dataset.project_id == project_id)
            .order_by(Dataset.created_at.desc())
        )
    )


@router.get("/datasets/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    return dataset
