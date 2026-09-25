"""Optional cloud LLM adapters; credentials stay in the OS credential vault."""
import httpx
import keyring

from app.domain.documents import DocumentError

SERVICE = "Document Intelligence Pipeline Lab"
HOSTS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta",
}


class CloudProvider:
    def __init__(self, provider_id: str):
        if provider_id not in HOSTS:
            raise ValueError("Unknown cloud provider")
        self.provider_id = provider_id

    def credential(self):
        try:
            secret = keyring.get_password(SERVICE, self.provider_id)
        except Exception as error:
            raise DocumentError("CREDENTIAL_STORE_UNAVAILABLE", "The operating system credential store is unavailable.", 503) from error
        if not secret:
            raise DocumentError("PROVIDER_NOT_CONFIGURED", "Add this provider's API key in Manage Providers.", 409)
        return secret

    def save_credential(self, secret: str):
        if not secret.strip() or len(secret) > 4096:
            raise DocumentError("INVALID_CREDENTIAL", "Enter a valid API key.", 422)
        try:
            keyring.set_password(SERVICE, self.provider_id, secret.strip())
        except Exception as error:
            raise DocumentError("CREDENTIAL_STORE_UNAVAILABLE", "The operating system credential store is unavailable.", 503) from error

    def remove_credential(self):
        try:
            keyring.delete_password(SERVICE, self.provider_id)
        except keyring.errors.PasswordDeleteError:
            pass

    def configured(self) -> bool:
        return bool(self.credential_or_none())

    def credential_or_none(self):
        try:
            return keyring.get_password(SERVICE, self.provider_id)
        except Exception:
            return None

    def _headers(self):
        key = self.credential()
        if self.provider_id == "openai":
            return {"Authorization": f"Bearer {key}"}
        if self.provider_id == "anthropic":
            return {"x-api-key": key, "anthropic-version": "2023-06-01"}
        return {"x-goog-api-key": key, "x-goog-api-client": "document-intelligence/0.4.0"}

    def _request(self, method, path, payload=None):
        try:
            with httpx.Client(base_url=HOSTS[self.provider_id], timeout=60) as client:
                response = client.request(method, path, headers=self._headers(), json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            message = "Provider rejected the request. Check credentials, model access, and account limits."
            raise DocumentError("PROVIDER_REQUEST_FAILED", f"{message} HTTP {status}.", 502) from error
        except (httpx.HTTPError, ValueError) as error:
            raise DocumentError("PROVIDER_UNAVAILABLE", "The provider could not be reached or returned an invalid response.", 503) from error

    def models(self) -> list[dict]:
        data = self._request("GET", "/models")
        if self.provider_id == "google":
            return [{"id": row["name"].removeprefix("models/"), "name": row.get("displayName", row["name"])}
                    for row in data.get("models", []) if "generateContent" in row.get("supportedGenerationMethods", [])]
        return [{"id": row["id"], "name": row.get("display_name", row["id"])}
                for row in data.get("data", []) if isinstance(row.get("id"), str)]

    def answer(self, system: str, prompt: str, model: str, temperature: float,
               max_output_tokens: int) -> str:
        if not model or len(model) > 160 or not all(c.isalnum() or c in "-._:/" for c in model):
            raise DocumentError("INVALID_MODEL", "Choose a model returned by Refresh Models.", 422)
        if self.provider_id == "openai":
            result = self._request("POST", "/responses", {"model": model, "instructions": system,
                "input": prompt, "temperature": temperature, "max_output_tokens": max_output_tokens})
            return "".join(part.get("text", "") for output in result.get("output", [])
                           for part in output.get("content", []) if part.get("type") == "output_text")
        if self.provider_id == "anthropic":
            result = self._request("POST", "/messages", {"model": model, "system": system,
                "messages": [{"role": "user", "content": prompt}], "temperature": temperature,
                "max_tokens": max_output_tokens})
            return "".join(part.get("text", "") for part in result.get("content", []) if part.get("type") == "text")
        result = self._request("POST", f"/models/{model}:generateContent", {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_output_tokens}})
        return "".join(part.get("text", "") for candidate in result.get("candidates", [])[:1]
                       for part in candidate.get("content", {}).get("parts", []))
