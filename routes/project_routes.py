from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from db.session import get_db
from models.project import Project
from schemas.project_schema import ProjectGitHubImport, ProjectResponse
from services.github_service import GitHubService

router = APIRouter(prefix="/projects", tags=["Projects & Code Storage"])


@router.post("/import-github", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def import_from_github(
    data: ProjectGitHubImport,
    user_id: int = Query(1, description="ID of the user importing the repo"),
    db: Session = Depends(get_db)
):
    """Clones a public GitHub repo and registers its metadata and file tree inside PostgreSQL."""
    result = GitHubService.clone_repository(
        db=db,
        github_url=data.github_url,
        user_id=user_id,
        project_title=data.title
    )

    project = db.query(Project).filter(Project.id == result["project_id"]).first()
    if not project:
        raise HTTPException(status_code=500, detail="Failed to retrieve saved project instance.")

    if data.description:
        project.description = data.description
        db.commit()
        db.refresh(project)

    return project


@router.post("/upload-zip", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def upload_project_zip(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    user_id: int = Form(1),
    db: Session = Depends(get_db)
):
    """Uploads a local ZIP code file and extracts its structure onto disk."""
    result = GitHubService.extract_zip_project(
        db=db,
        file=file,
        user_id=user_id,
        project_title=title
    )

    project = db.query(Project).filter(Project.id == result["project_id"]).first()
    if not project:
        raise HTTPException(status_code=500, detail="Failed to retrieve saved project instance.")

    if description:
        project.description = description
        db.commit()
        db.refresh(project)

    return project


@router.post("/{project_id}/sync", response_model=ProjectResponse)
def sync_project_github(
    project_id: int, 
    user_id: int = Query(1, description="ID of the project owner"),
    db: Session = Depends(get_db)
):
    """Triggers `git pull` on an existing imported GitHub project to fetch changes."""
    result = GitHubService.sync_pull_repo(
        db=db,
        project_id=project_id,
        user_id=user_id
    )

    project = db.query(Project).filter(Project.id == result["project_id"]).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found after synchronization.")

    return project