from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List
from db.session import get_db
from models.post import Post
from schemas.post_schema import PostResponse
from services.post_service import PostService

router = APIRouter(prefix="/posts", tags=["Community Posts & Media"])


@router.post("/create", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_project_post(
    title: str = Form(..., description="Title of the post"),
    content: Optional[str] = Form(None, description="Body text or markdown response"),
    project_url: Optional[str] = Form(None, description="External project or live demo link"),
    project_id: Optional[int] = Form(None, description="Optional ID of imported GitHub/ZIP project"),
    files: Optional[List[UploadFile]] = File(None, description="Images, Videos, PDFs, or PPTs (Max 5)"),
    user_id: int = Query(1, description="ID of the post author"),
    db: Session = Depends(get_db)
):
    """Creates a new post supporting multi-media uploads (Images, Videos, PDFs, PPTs), text, and project links."""
    return PostService.create_post(
        db=db,
        user_id=user_id,
        title=title,
        content=content,
        project_url=project_url,
        project_id=project_id,
        files=files
    )


@router.get("/{post_id}", response_model=PostResponse)
def get_post_by_id(post_id: int, db: Session = Depends(get_db)):
    """Fetches a specific post by ID."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    return post