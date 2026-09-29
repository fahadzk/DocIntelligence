"""Local Ollama chat provider using its HTTP API."""
import httpx

from app.domain.documents import DocumentError
from app.plugins.chunking_output import chunk_boundary_schema


class OllamaProvider:
    """Calls the local Ollama server with a non-streaming chat request."""

    def __init__(self, base_url: str = "http://localhost:11434", timeout_seconds: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                response = client.request(method, path, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise DocumentError("OLLAMA_REQUEST_FAILED", f"Ollama returned HTTP {error.response.status_code}.", 502) from error
        except (httpx.HTTPError, ValueError) as error:
            raise DocumentError("OLLAMA_UNAVAILABLE", f"Could not reach the Ollama server at {self.base_url}.", 503) from error

    def version(self) -> str:
        value = self._request("GET", "/api/version").get("version")
        return str(value or "unknown")

    def models(self) -> list[dict]:
        data = self._request("GET", "/api/tags")
        return [{"id": item["name"], "name": item["name"]} for item in data.get("models", [])
                if isinstance(item.get("name"), str)]

    def answer_chunk(self, system: str, prompt: str, model: str, *, paragraph_count: int = 12) -> str:
        if not model or len(model) > 160:
            raise DocumentError("INVALID_MODEL", "Choose an installed Ollama model.", 422)
        result = self._request("POST", "/api/chat", {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "stream": False, "think": False, "format": chunk_boundary_schema(paragraph_count),
            "options": {"temperature": 0, "num_predict": 512},
        })
        return result.get("message", {}).get("content", "")

    def answer(self, system: str, prompt: str, model: str, temperature: float,
               max_output_tokens: int) -> str:
        if not model or len(model) > 160:
            raise DocumentError("INVALID_MODEL", "Choose an installed Ollama model.", 422)
        result = self._request("POST", "/api/chat", {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_output_tokens},
        })
        return result.get("message", {}).get("content", "")
