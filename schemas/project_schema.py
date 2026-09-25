from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime

class ProjectGitHubImport(BaseModel):
    title: str
    description: Optional[str] = None
    github_url: str

class ProjectResponse(BaseModel):
    id: int
    uuid: str
    user_id: int
    title: str
    description: Optional[str] = None
    source_type: str
    github_url: Optional[str] = None
    disk_directory: str
    disk_size_bytes: int
    file_tree: Optional[Dict[str, Any]] = None
    created_at: datetime
    last_synced_at: datetime

    class Config:
        from_attributes = True