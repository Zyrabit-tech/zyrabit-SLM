"""
Structured JSON Extraction Service.
Enables reliable, zero-hallucination structured entity and document extraction for mission-critical apps.
"""

from __future__ import annotations

import json
import re
import logging
from typing import Any, Dict, Optional
from app.ports.inference_port import InferenceProviderPort, InferenceRequest

logger = logging.getLogger("zyrabit.structured_extraction")


class StructuredExtractionService:
    def __init__(self, inference_provider: InferenceProviderPort):
        self.inference_provider = inference_provider

    @staticmethod
    def extract_json_block(text: str) -> Optional[dict]:
        """Extracts and parses a JSON object from model output text, stripping code fences if present."""
        text = text.strip()
        
        # 1. Try direct parse
        try:
            return json.loads(text)
        except Exception:
            pass

        # 2. Try markdown fenced block ```json ... ``` or ``` ... ```
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        matches = re.findall(pattern, text)
        for block in matches:
            try:
                return json.loads(block.strip())
            except Exception:
                continue

        # 3. Try finding outer curly braces {...}
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = text[first_brace : last_brace + 1]
            try:
                return json.loads(candidate)
            except Exception:
                pass

        return None

    @staticmethod
    def validate_schema(data: dict, schema: dict) -> tuple[bool, list[str]]:
        """
        Validates extracted data against schema definition.
        Checks required fields and basic types.
        """
        errors = []
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: '{field}'")

        properties = schema.get("properties", {})
        type_mapping = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        for prop, prop_spec in properties.items():
            if prop in data and data[prop] is not None:
                expected_type_str = prop_spec.get("type")
                if expected_type_str in type_mapping:
                    expected_type = type_mapping[expected_type_str]
                    if not isinstance(data[prop], expected_type):
                        errors.append(
                            f"Field '{prop}' has invalid type: expected {expected_type_str}, got {type(data[prop]).__name__}"
                        )

        return len(errors) == 0, errors

    async def extract(
        self,
        text: str,
        schema: dict,
        instructions: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extracts structured JSON conforming to schema from input text.
        """
        schema_json = json.dumps(schema, indent=2, ensure_ascii=False)
        system_prompt = (
            "You are a strict, zero-hallucination data extraction engine. "
            "Your task is to extract information from the provided user text and format it ONLY as a valid JSON object matching the requested schema.\n\n"
            "RULES:\n"
            "1. Output MUST be a valid JSON object matching the schema.\n"
            "2. Do NOT include markdown commentary, conversational pleasantries, or explanations outside the JSON block.\n"
            "3. If a field is not present or mentioned in the text, use null (or empty list [] for array fields).\n"
            "4. Never invent or hallucinate data not found in the source text."
        )

        user_content = (
            f"INPUT TEXT:\n\"\"\"\n{text}\n\"\"\"\n\n"
            f"REQUIRED JSON SCHEMA:\n```json\n{schema_json}\n```\n"
        )
        if instructions:
            user_content += f"\nADDITIONAL INSTRUCTIONS:\n{instructions}\n"

        user_content += "\nRespond with the JSON object now:"

        request = InferenceRequest(
            model=model or "default",
            prompt=user_content,
            system_prompt=system_prompt,
            options={"temperature": 0.0, "max_tokens": 2048},
        )

        result = self.inference_provider.generate(request)
        raw_output = result.text.strip()
        parsed_data = self.extract_json_block(raw_output)

        if parsed_data is None:
            return {
                "data": {},
                "valid": False,
                "errors": ["Failed to parse valid JSON from model response"],
                "raw_response": raw_output,
                "model": result.raw_payload.get("model") or result.provider or model or "unknown",
            }

        is_valid, validation_errors = self.validate_schema(parsed_data, schema)

        return {
            "data": parsed_data,
            "valid": is_valid,
            "errors": validation_errors,
            "raw_response": raw_output,
            "model": result.raw_payload.get("model") or result.provider or model or "unknown",
        }
