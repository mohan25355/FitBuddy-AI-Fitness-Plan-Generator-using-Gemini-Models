from __future__ import annotations

import json
from typing import Any, TypeVar

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import logger


SchemaT = TypeVar("SchemaT")


class GeminiServiceError(RuntimeError):
    pass


class GeminiService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None

    def _ensure_client(self) -> genai.Client:
        if not self.client:
            raise GeminiServiceError("Gemini API key is not configured.")
        return self.client

    def _generate_text(self, model: str, prompt: str) -> str:
        client = self._ensure_client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                response_mime_type="application/json",
                max_output_tokens=4096,
            ),
        )
        return (response.text or "").strip()

    def _parse_json_payload(self, payload: str) -> dict[str, Any]:
        try:
            return json.loads(payload)
        except json.JSONDecodeError as error:
            logger.warning("Gemini returned malformed JSON: %s", error)
            return self._attempt_repair(payload)

    def _attempt_repair(self, payload: str) -> dict[str, Any]:
        client = self._ensure_client()
        repair_prompt = (
            "Repair the following JSON so it becomes valid JSON only. "
            "Preserve the original structure and values where possible.\n\n"
            f"{payload}"
        )
        response = client.models.generate_content(
            model=self.settings.default_fast_model,
            contents=repair_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                max_output_tokens=2048,
            ),
        )
        repaired = (response.text or "").strip()
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as error:
            raise GeminiServiceError("Gemini returned invalid structured data.") from error

    def generate_structured(self, *, model: str, prompt: str, schema: type[SchemaT]) -> SchemaT:
        try:
            payload = self._generate_text(model=model, prompt=prompt)
            raw = self._parse_json_payload(payload)
            return schema.model_validate(raw)
        except ValidationError as error:
            logger.warning("Gemini validation error: %s", error)
            raise GeminiServiceError("Generated data did not match the required schema.") from error