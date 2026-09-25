from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class MediaAttachmentSchema(BaseModel):
    file_name: str
    file_path: str
    media_type: str  # "image", "video", "pdf", "presentation"
    size_bytes: int


class PostResponse(BaseModel):
    id: int
    uuid: str
    user_id: int
    project_id: Optional[int] = None
    title: str
    content: Optional[str] = None
    project_url: Optional[str] = None
    media_attachments: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True