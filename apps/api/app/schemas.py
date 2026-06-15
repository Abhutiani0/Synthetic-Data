from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    industry: str = "general"
    use_case: str = ""


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    industry: str
    use_case: str
    status: str
    created_at: datetime


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    filename: str
    row_count: int
    column_count: int
    profile_json: dict[str, Any]
    created_at: datetime


class GenerateRequest(BaseModel):
    row_count: int = Field(default=1000, ge=1, le=1_000_000)
    preserve_correlations: bool = True
    add_noise: bool = True
    seed: int | None = None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    dataset_id: int | None
    mode: str
    generator_type: str
    status: str
    row_count: int
    settings_json: dict[str, Any]
    created_at: datetime


class PreviewOut(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    synthetic_run_id: int
    privacy_score: float
    utility_score: float
    risk_level: str
    metrics_json: dict[str, Any]
    report_text: str
    generated_by: str
    approved_status: str
    created_at: datetime


class ApprovalUpdate(BaseModel):
    approved_status: str
