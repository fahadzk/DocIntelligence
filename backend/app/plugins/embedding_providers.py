"""Embedding adapters for Ollama and OpenAI-compatible HTTP services."""
from __future__ import annotations

from collections.abc import Callable

import httpx

from app.domain.documents import DocumentError


def _validate_model(model: str) -> str:
    if not model or len(model) > 200 or not all(character.isalnum() or character in "-._:/" for character in model):
        raise DocumentError("INVALID_MODEL", "Choose an embedding model returned by the provider.", 422)
    return model


class OllamaEmbeddings:
    def __init__(self, base_url: str, timeout_seconds: int, model: str):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.model = model

    @property
    def ready(self) -> bool:
        return bool(self.model)

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                response = client.request(method, path, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise DocumentError("EMBEDDING_REQUEST_FAILED", f"Ollama returned HTTP {error.response.status_code}.", 502) from error
        except (httpx.HTTPError, ValueError) as error:
            raise DocumentError("EMBEDDING_PROVIDER_UNAVAILABLE", f"Could not reach Ollama at {self.base_url}.", 503) from error

    def models(self) -> list[dict]:
        data = self._request("GET", "/api/tags")
        return [{"id": item["name"], "name": item["name"]} for item in data.get("models", [])
                if isinstance(item.get("name"), str)]

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        result = self._request("POST", "/api/embed", {"model": _validate_model(self.model), "input": texts})
        vectors = result.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(texts) or not all(isinstance(row, list) for row in vectors):
            raise DocumentError("INVALID_EMBEDDING_RESPONSE", "Ollama returned an invalid embedding response.", 502)
        return vectors


class OpenAICompatibleEmbeddings:
    def __init__(self, base_url: str, timeout_seconds: int, model: str,
                 credential: Callable[[], str | None]):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.model = model
        self.credential = credential

    @property
    def ready(self) -> bool:
        return bool(self.model and self.credential())

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        secret = self.credential()
        if not secret:
            raise DocumentError("PROVIDER_NOT_CONFIGURED", "Add an API key to this embedding plugin.", 409)
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                response = client.request(method, path, headers={"Authorization": f"Bearer {secret}"}, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise DocumentError("EMBEDDING_REQUEST_FAILED", f"The embedding provider returned HTTP {error.response.status_code}.", 502) from error
        except (httpx.HTTPError, ValueError) as error:
            raise DocumentError("EMBEDDING_PROVIDER_UNAVAILABLE", "The embedding provider could not be reached or returned invalid data.", 503) from error

    def models(self) -> list[dict]:
        data = self._request("GET", "/models")
        return [{"id": item["id"], "name": item.get("name", item["id"])}
                for item in data.get("data", []) if isinstance(item.get("id"), str)]

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        result = self._request("POST", "/embeddings", {"model": _validate_model(self.model), "input": texts})
        rows = sorted(result.get("data", []), key=lambda item: item.get("index", 0))
        vectors = [item.get("embedding") for item in rows]
        if len(vectors) != len(texts) or not all(isinstance(row, list) for row in vectors):
            raise DocumentError("INVALID_EMBEDDING_RESPONSE", "The provider returned an invalid embedding response.", 502)
        return vectors
