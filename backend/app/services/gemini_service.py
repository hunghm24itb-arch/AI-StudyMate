import json
import random
import re
import time
from typing import Any, Type

from google import genai
from google.genai.errors import APIError
from google.genai import types
from pydantic import BaseModel

from app.config import settings


_TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3
_INITIAL_RETRY_DELAY_SECONDS = 1.0
_EMBEDDING_BATCH_SIZE = 100
_RETRY_DELAY_PATTERN = re.compile(r"retry in\s+(\d+(?:\.\d+)?)\s*s", re.IGNORECASE)


class GeminiService:
    def __init__(self) -> None:
        self.client = None
        if settings.gemini_api_key:
            self.client = genai.Client(api_key=settings.gemini_api_key)

    def _require_client(self) -> None:
        if not self.client:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

    @staticmethod
    def _with_transient_retry(operation):
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return operation()
            except APIError as exc:
                if exc.code not in _TRANSIENT_STATUS_CODES or attempt == _MAX_ATTEMPTS - 1:
                    raise
                server_delay = GeminiService._server_retry_delay(exc)
                if server_delay is not None:
                    delay = server_delay + random.uniform(0, min(1.0, server_delay * 0.1))
                else:
                    delay = _INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt)
                    delay = random.uniform(delay / 2, delay)
                time.sleep(delay)

    @staticmethod
    def _server_retry_delay(error: APIError) -> float | None:
        response_headers = getattr(getattr(error, "response", None), "headers", {}) or {}
        retry_after = response_headers.get("retry-after")
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass

        details = getattr(error, "details", {}) or {}
        api_error = details.get("error", details) if isinstance(details, dict) else {}
        retry_details = api_error.get("details", []) if isinstance(api_error, dict) else []
        for item in retry_details:
            if not isinstance(item, dict) or not item.get("@type", "").endswith("google.rpc.RetryInfo"):
                continue
            retry_delay = item.get("retryDelay", item.get("retry_delay"))
            if isinstance(retry_delay, dict):
                seconds = float(retry_delay.get("seconds", 0))
                nanos = float(retry_delay.get("nanos", 0))
                return max(0.0, seconds + nanos / 1_000_000_000)
            if isinstance(retry_delay, str):
                match = re.fullmatch(r"(\d+(?:\.\d+)?)s", retry_delay.strip())
                if match:
                    return max(0.0, float(match.group(1)))

        match = _RETRY_DELAY_PATTERN.search(error.message or "")
        if match:
            return max(0.0, float(match.group(1)))
        return None

    @staticmethod
    def _extract_text(response: Any) -> str:
        if hasattr(response, "text") and response.text:
            return response.text
        if hasattr(response, "candidates") and response.candidates:
            content = response.candidates[0].content
            if hasattr(content, "parts"):
                parts = []
                for part in content.parts:
                    if hasattr(part, "text"):
                        parts.append(part.text)
                if parts:
                    return "".join(parts)
        return str(response)

    @staticmethod
    def _clean_json_text(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        self._require_client()
        config = types.GenerateContentConfig(system_instruction=system_instruction) if system_instruction else None
        response = self._with_transient_retry(
            lambda: self.client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=config,
            )
        )
        return self._extract_text(response)

    def generate_json(self, prompt: str, schema: Type[BaseModel], system_instruction: str | None = None) -> BaseModel:
        self._require_client()
        final_system_instruction = (
            system_instruction
            or "Return only valid JSON with no markdown fences and no extra commentary."
        )
        config = types.GenerateContentConfig(
            system_instruction=final_system_instruction,
            response_mime_type="application/json",
            response_schema=schema,
        )
        response = self._with_transient_retry(
            lambda: self.client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=config,
            )
        )
        raw = self._clean_json_text(self._extract_text(response))
        data = json.loads(raw)
        return schema.model_validate(data)

    def embed_text(self, text: str) -> list[float]:
        self._require_client()
        response = self._with_transient_retry(
            lambda: self.client.models.embed_content(
                model=settings.gemini_embedding_model,
                contents=text,
            )
        )
        embeddings = response.embeddings
        if not embeddings:
            raise ValueError("Gemini did not return an embedding.")
        values = embeddings[0].values if hasattr(embeddings[0], "values") else embeddings[0]
        return list(values)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self._require_client()
        if not texts:
            return []
        document_embeddings: list[list[float]] = []
        for batch_start in range(0, len(texts), _EMBEDDING_BATCH_SIZE):
            batch = texts[batch_start:batch_start + _EMBEDDING_BATCH_SIZE]
            response = self._with_transient_retry(
                lambda: self.client.models.embed_content(
                    model=settings.gemini_embedding_model,
                    contents=batch,
                )
            )
            embeddings = getattr(response, "embeddings", None) or []
            if len(embeddings) != len(batch):
                raise ValueError(
                    f"Gemini returned {len(embeddings)} embeddings for {len(batch)} chunks "
                    f"in the batch starting at index {batch_start}; expected one embedding per chunk."
                )
            document_embeddings.extend(
                list(item.values if hasattr(item, "values") else item)
                for item in embeddings
            )

        if len(document_embeddings) != len(texts):
            raise ValueError(
                f"Gemini returned {len(document_embeddings)} embeddings for {len(texts)} document chunks."
            )
        return document_embeddings
