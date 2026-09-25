from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class CodeReviewRequest(BaseModel):
    code_snippet: str
    programming_language: Optional[str] = "python"


class CodeExplainRequest(BaseModel):
    code_snippet: str
    target_audience: Optional[str] = "developer"  # e.g., "beginner", "developer", "non-technical"


class CodeReviewResponse(BaseModel):
    model: str = "chetan272006/Qwen2.5-Coder-3B-Instruct"
    status: str
    score: Optional[int] = 100
    issues: List[str] = []
    suggestions: List[str] = []


class CodeExplainResponse(BaseModel):
    model: str = "chetan272006/Qwen2.5-Coder-3B-Instruct"
    target_audience: str
    explanation: str