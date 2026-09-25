import os
import uuid
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from models.post import Post
from models.project import Project

logger = logging.getLogger("devsocial.security")

BASE_MEDIA_DIR = os.path.abspath(os.getenv("MEDIA_DIR", "uploads"))
POSTS_MEDIA_ROOT = Path(os.path.join(BASE_MEDIA_DIR, "posts")).resolve()

# Strict Multi-Media Upload Limits
MAX_IMAGE_SIZE_BYTES = 15 * 1024 * 1024       # 15 MB per image
MAX_DOCUMENT_SIZE_BYTES = 50 * 1024 * 1024    # 50 MB per PDF / PPT
MAX_VIDEO_SIZE_BYTES = 100 * 1024 * 1024     # 100 MB per Video
MAX_TOTAL_POST_FILES = 5                      # Max 5 files per post

# Allowed Extension Mappings
ALLOWED_MEDIA_TYPES = {
    "image": {".jpg", ".jpeg", ".png", ".webp", ".gif"},
    "video": {".mp4", ".mov", ".mkv", ".webm"},
    "pdf": {".pdf"},
    "presentation": {".ppt", ".pptx"}
}


class PostService:

    @classmethod
    def initialize_storage(cls):
        """Ensures the posts media storage directory exists."""
        POSTS_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _classify_and_validate_file(cls, file: UploadFile) -> str:
        """Validates file extensions against allowed media categories."""
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename missing.")

        ext = Path(file.filename).suffix.lower()
        for media_category, extensions in ALLOWED_MEDIA_TYPES.items():
            if ext in extensions:
                return media_category

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed types: Images, Videos, PDFs, PPT/PPTX."
        )

    @classmethod
    def create_post(
        cls,
        db: Session,
        user_id: int,
        title: str,
        content: Optional[str] = None,
        project_url: Optional[str] = None,
        project_id: Optional[int] = None,
        files: Optional[List[UploadFile]] = None
    ) -> Post:
        """Processes post media attachments, validates limits, and saves DB record."""
        cls.initialize_storage()

        # Validate associated project if supplied
        if project_id:
            project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
            if not project:
                raise HTTPException(status_code=404, detail="Associated project not found or unauthorized.")

        attachments: List[Dict[str, Any]] = []

        if files:
            if len(files) > MAX_TOTAL_POST_FILES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Maximum {MAX_TOTAL_POST_FILES} attachments allowed per post."
                )

            user_posts_dir = POSTS_MEDIA_ROOT / f"user_{user_id}"
            user_posts_dir.mkdir(parents=True, exist_ok=True)

            for file in files:
                category = cls._classify_and_validate_file(file)
                file_uuid = str(uuid.uuid4())
                ext = Path(file.filename).suffix.lower()
                saved_filename = f"{file_uuid}{ext}"
                target_path = user_posts_dir / saved_filename

                # Stream upload and enforce size limits
                file_size = 0
                max_size = (
                    MAX_VIDEO_SIZE_BYTES if category == "video"
                    else MAX_DOCUMENT_SIZE_BYTES if category in {"pdf", "presentation"}
                    else MAX_IMAGE_SIZE_BYTES
                )

                try:
                    with open(target_path, "wb") as buffer:
                        while chunk := file.file.read(1024 * 1024):
                            file_size += len(chunk)
                            if file_size > max_size:
                                limit_mb = max_size // (1024 * 1024)
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"File '{file.filename}' exceeds maximum allowed size of {limit_mb} MB for {category}s."
                                )
                            buffer.write(chunk)
                except Exception as e:
                    if target_path.exists():
                        os.remove(target_path)
                    if isinstance(e, HTTPException):
                        raise e
                    logger.error(f"[POST_UPLOAD_ERROR] Failed to save post attachment: {str(e)}")
                    raise HTTPException(status_code=500, detail="Failed to save media attachments.")

                attachments.append({
                    "file_name": file.filename,
                    "saved_path": str(target_path),
                    "media_type": category,
                    "size_bytes": file_size
                })

        # Save Post Entity
        post = Post(
            user_id=user_id,
            project_id=project_id,
            title=title.strip(),
            content=content.strip() if content else None,
            project_url=project_url.strip() if project_url else None,
            media_attachments=attachments
        )

        db.add(post)
        db.commit()
        db.refresh(post)
        return post