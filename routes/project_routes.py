from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from db.session import get_db
from models.project import Project
from schemas.project_schema import ProjectGitHubImport, ProjectResponse
from services.github_service import GitHubService

router = APIRouter(prefix="/projects", tags=["Projects & Code Storage"])

@router.post("/import-github", response_model=ProjectResponse)
def import_from_github(
    data: ProjectGitHubImport,
    user_id: int = 1,  # Temporary fixed ID until JWT route dependency is attached
    db: Session = Depends(get_db)
):
    """Clones a public GitHub repo and stores its structure on local disk."""
    result = GitHubService.clone_repository(
        github_url=str(data.github_url),
        user_id=user_id,
        project_name=data.title
    )

    project = Project(
        user_id=user_id,
        title=data.title,
        description=data.description,
        source_type="GITHUB",
        github_url=str(data.github_url),
        local_path=result["local_path"],
        file_tree=result["file_tree"]
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@router.post("/upload-zip", response_model=ProjectResponse)
def upload_project_zip(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """Uploads a local ZIP code file and extracts its structure."""
    result = GitHubService.extract_zip_project(
        file=file,
        user_id=user_id,
        project_name=title
    )

    project = Project(
        user_id=user_id,
        title=title,
        description=description,
        source_type="ZIP",
        github_url=None,
        local_path=result["local_path"],
        file_tree=result["file_tree"]
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@router.post("/{project_id}/sync", response_model=ProjectResponse)
def sync_project_github(project_id: int, db: Session = Depends(get_db)):
    """Triggers `git pull` on an existing imported GitHub project to fetch changes."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.source_type != "GITHUB":
        raise HTTPException(status_code=400, detail="Cannot sync ZIP-uploaded projects.")

    GitHubService.sync_pull_repo(project.local_path)
    project.file_tree = GitHubService.build_file_tree(project.local_path)
    db.commit()
    db.refresh(project)
    return project