from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Project, SyntheticRun
from ..schemas import ProjectCreate, ProjectOut, RunOut

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.created_at.desc())))


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/{project_id}/runs", response_model=list[RunOut])
def list_project_runs(project_id: int, db: Session = Depends(get_db)) -> list[SyntheticRun]:
    return list(
        db.scalars(
            select(SyntheticRun)
            .where(SyntheticRun.project_id == project_id)
            .order_by(SyntheticRun.created_at.desc())
        )
    )


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    db.delete(project)
    db.commit()
    return {"deleted": True}
