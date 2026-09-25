import logging
import json
import torch
from typing import Dict, Any, Optional
from fastapi import HTTPException
from transformers import pipeline

logger = logging.getLogger("devsocial.ai")

MODEL_ID = "chetan272006/Qwen2.5-Coder-3B-Instruct"


class AICodeService:
    _pipe = None

    @classmethod
    def get_pipeline(cls):
        """Lazy-loads the Hugging Face generation pipeline as a singleton."""
        if cls._pipe is None:
            logger.info(f"Loading fine-tuned model: {MODEL_ID}...")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            torch_dtype = torch.float16 if device == "cuda" else torch.float32

            try:
                cls._pipe = pipeline(
                    "text-generation",
                    model=MODEL_ID,
                    torch_dtype=torch_dtype,
                    device_map="auto" if device == "cuda" else None,
                )
                logger.info(f"Successfully loaded {MODEL_ID} on device: {device}")
            except Exception as e:
                logger.error(f"[AI_MODEL_LOAD_ERROR] Failed to load model {MODEL_ID}: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to initialize AI Code Model on server.")
        return cls._pipe

    @classmethod
    def review_code(cls, code_snippet: str, programming_language: Optional[str] = "python") -> Dict[str, Any]:
        """Runs automated code review using your fine-tuned model."""
        pipe = cls.get_pipeline()

        system_prompt = (
            "You are an expert AI code reviewer. Your task is to analyze the user's source code for "
            "security vulnerabilities, performance bottlenecks, syntax errors, and anti-patterns. "
            "Return a strictly valid JSON response with keys: 'status' ('PASSED', 'WARNING', or 'FAILED'), "
            "'score' (1-100), 'issues' (list of strings), and 'suggestions' (list of strings)."
        )

        user_content = f"Language: {programming_language}\n\nCode to review:\n```\n{code_snippet}\n```"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            outputs = pipe(
                messages,
                max_new_tokens=1024,
                temperature=0.2,
                top_p=0.9,
                do_sample=False
            )

            # Extract generated response content
            generated_text = outputs[0]["generated_text"][-1]["content"].strip()

            # Clean markdown code blocks if the model wrapped JSON in ```json ... ```
            clean_json = generated_text
            if "```" in clean_json:
                clean_json = clean_json.split("```")[1]
                if clean_json.startswith("json"):
                    clean_json = clean_json[4:].strip()

            try:
                parsed_json = json.loads(clean_json)
                return parsed_json
            except json.JSONDecodeError:
                return {
                    "status": "COMPLETED",
                    "score": 80,
                    "issues": [],
                    "suggestions": [generated_text]
                }

        except Exception as e:
            logger.error(f"[AI_REVIEW_ERROR] Code review generation failed: {str(e)}")
            raise HTTPException(status_code=500, detail="AI code review generation failed.")

    @classmethod
    def explain_code(cls, code_snippet: str, target_audience: Optional[str] = "developer") -> Dict[str, Any]:
        """Generates line-by-line and conceptual code explanations."""
        pipe = cls.get_pipeline()

        system_prompt = (
            f"You are an expert AI code explainer. Explain the provided code clearly for a {target_audience}. "
            "Break down what the code does, high-level logic, key algorithms/data structures used, "
            "and line-by-line or function-level details."
        )

        user_content = f"Please explain this code:\n```\n{code_snippet}\n```"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            outputs = pipe(
                messages,
                max_new_tokens=1024,
                temperature=0.3,
                top_p=0.95,
                do_sample=True
            )

            explanation = outputs[0]["generated_text"][-1]["content"].strip()
            return {
                "explanation": explanation,
                "target_audience": target_audience
            }

        except Exception as e:
            logger.error(f"[AI_EXPLAIN_ERROR] Code explanation generation failed: {str(e)}")
            raise HTTPException(status_code=500, detail="AI code explanation failed.")