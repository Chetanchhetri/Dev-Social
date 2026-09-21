from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Any, Dict
from datetime import datetime

class ProjectGitHubImport(BaseModel):
    title: str
    description: Optional[str] = None
    github_url: HttpUrl

class ProjectResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    source_type: str
    github_url: Optional[str]
    local_path: str
    file_tree: List[Dict[str, Any]]
    created_at: datetime
    last_synced_at: datetime

    class Config:
        from_attributes = True