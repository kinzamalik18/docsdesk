"""Gemini API client over plain HTTPS, so there is no SDK version to keep in sync."""

import logging
import time

import httpx

from app.llm.base import normalize

log = logging.getLogger(__name__)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
RETRY_STATUSES = {429, 500, 502, 503, 504}
BATCH_LIMIT = 100  # documents per batchEmbedContents request


class GeminiError(RuntimeError):
    pass


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, chat_model: str, embed_model: str, dim: int, timeout: float = 60):
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.dim = dim
        self.client = httpx.Client(
            base_url=BASE_URL,
            headers={"x-goog-api-key": api_key, "content-type": "application/json"},
            timeout=timeout,
        )

    def _post(self, path: str, payload: dict, attempts: int = 5) -> dict:
        delay = 2.0
        for attempt in range(1, attempts + 1):
            response = self.client.post(path, json=payload)
            if response.status_code < 400:
                return response.json()
            if response.status_code in RETRY_STATUSES and attempt < attempts:
                wait = float(response.headers.get("retry-after", delay))
                log.warning("Gemini returned %s, retrying in %.0fs", response.status_code, wait)
                time.sleep(wait)
                delay = min(delay * 2, 30)
                continue
            raise GeminiError(f"Gemini API error {response.status_code}: {response.text[:300]}")
        raise GeminiError("Gemini API kept failing after retries")

    def _embed_request(self, text: str, task_type: str) -> dict:
        return {
            "model": f"models/{self.embed_model}",
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
            "outputDimensionality": self.dim,
        }

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), BATCH_LIMIT):
            batch = texts[start : start + BATCH_LIMIT]
            data = self._post(
                f"/models/{self.embed_model}:batchEmbedContents",
                {"requests": [self._embed_request(t, "RETRIEVAL_DOCUMENT") for t in batch]},
            )
            vectors.extend(normalize(e["values"]) for e in data["embeddings"])
        return vectors

    def embed_query(self, text: str) -> list[float]:
        data = self._post(
            f"/models/{self.embed_model}:embedContent",
            self._embed_request(text, "RETRIEVAL_QUERY"),
        )
        return normalize(data["embedding"]["values"])

    def generate_json(self, system: str, prompt: str) -> str:
        data = self._post(
            f"/models/{self.chat_model}:generateContent",
            {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
            },
        )
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError) as exc:
            # Happens when the response is blocked by safety filters or empty.
            raise GeminiError(f"Gemini returned no content: {str(data)[:300]}") from exc
        return "".join(p.get("text", "") for p in parts)
