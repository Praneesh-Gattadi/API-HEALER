import os
import json
from typing import Any, Dict
from google import genai
from pydantic import ValidationError

from app.models.diff_result import DiffResult
from app.models.migration_plan import MigrationPlan

def get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    return genai.Client(api_key=api_key)

async def generate_plan_with_llm(diff: DiffResult, old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> MigrationPlan:
    """
    Uses the Google GenAI SDK to parse the diff into a structured MigrationPlan.
    Raises exceptions on failure (handled by caller).
    """
    client = get_client()
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    prompt = f"""
You are an expert API integration engineer.
Given the deterministic diff of an OpenAPI specification (DiffResult), your task is to create a structured MigrationPlan.

DiffResult:
{diff.model_dump_json(indent=2)}

Analyze the diff and provide actionable steps to migrate consumers to the new API contract.
"""
    
    # Using the new google-genai structured output support
    # We call generate_content natively wrapping it in an asyncio interface if needed,
    # but the google-genai SDK provides an async client natively.
    
    response = await client.aio.models.generate_content(
        model=model_name,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MigrationPlan,
        ),
    )
    
    if not response.text:
        raise ValueError("Empty response from Gemini")
        
    try:
        # The response text should be a JSON matching the MigrationPlan schema
        plan_data = json.loads(response.text)
        return MigrationPlan.model_validate(plan_data)
    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError(f"Failed to validate LLM output: {e}")
