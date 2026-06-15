from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> datetime:
    return datetime.utcnow()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    industry: Mapped[str] = mapped_column(String(100), default="general")
    use_case: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    datasets: Mapped[list["Dataset"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    runs: Mapped[list["SyntheticRun"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    # Full per-column profile incl. detected type, risk and stats.
    profile_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    project: Mapped["Project"] = relationship(back_populates="datasets")


class SyntheticRun(Base):
    __tablename__ = "synthetic_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    dataset_id: Mapped[int | None] = mapped_column(
        ForeignKey("datasets.id"), nullable=True
    )
    mode: Mapped[str] = mapped_column(String(50), default="synthesize")
    generator_type: Mapped[str] = mapped_column(String(50), default="statistical")
    status: Mapped[str] = mapped_column(String(50), default="generated")
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)
    file_path: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    project: Mapped["Project"] = relationship(back_populates="runs")
    report: Mapped["SafetyReport | None"] = relationship(
        back_populates="run", cascade="all, delete-orphan", uselist=False
    )


class SafetyReport(Base):
    __tablename__ = "safety_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    synthetic_run_id: Mapped[int] = mapped_column(ForeignKey("synthetic_runs.id"))
    privacy_score: Mapped[float] = mapped_column(Float, default=0.0)
    utility_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(50), default="unknown")
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    report_text: Mapped[str] = mapped_column(Text, default="")
    generated_by: Mapped[str] = mapped_column(String(50), default="local")
    approved_status: Mapped[str] = mapped_column(String(50), default="needs_review")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    run: Mapped["SyntheticRun"] = relationship(back_populates="report")
