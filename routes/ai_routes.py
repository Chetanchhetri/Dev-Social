from fastapi import APIRouter, HTTPException, status
from schemas.ai_schema import CodeReviewRequest, CodeReviewResponse, CodeExplainRequest, CodeExplainResponse
from services.ai_code_service import AICodeService

router = APIRouter(prefix="/ai", tags=["AI Code Reviewer & Explainer"])


@router.post("/review", response_model=CodeReviewResponse, status_code=status.HTTP_200_OK)
def review_code(payload: CodeReviewRequest):
    """Audits source code for security flaws, bugs, performance, and best practices."""
    if not payload.code_snippet or not payload.code_snippet.strip():
        raise HTTPException(status_code=400, detail="Code snippet cannot be empty.")

    if len(payload.code_snippet) > 15000:
        raise HTTPException(status_code=400, detail="Code snippet exceeds character limit of 15,000 chars.")

    result = AICodeService.review_code(
        code_snippet=payload.code_snippet,
        programming_language=payload.programming_language
    )

    return {
        "model": "chetan272006/Qwen2.5-Coder-3B-Instruct",
        "status": result.get("status", "COMPLETED"),
        "score": result.get("score", 100),
        "issues": result.get("issues", []),
        "suggestions": result.get("suggestions", [])
    }


@router.post("/explain", response_model=CodeExplainResponse, status_code=status.HTTP_200_OK)
def explain_code(payload: CodeExplainRequest):
    """Explains source code logic, architecture, and line-by-line flow."""
    if not payload.code_snippet or not payload.code_snippet.strip():
        raise HTTPException(status_code=400, detail="Code snippet cannot be empty.")

    if len(payload.code_snippet) > 15000:
        raise HTTPException(status_code=400, detail="Code snippet exceeds character limit of 15,000 chars.")

    result = AICodeService.explain_code(
        code_snippet=payload.code_snippet,
        target_audience=payload.target_audience
    )

    return {
        "model": "chetan272006/Qwen2.5-Coder-3B-Instruct",
        "target_audience": result["target_audience"],
        "explanation": result["explanation"]
    }