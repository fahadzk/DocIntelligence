"""Declarative plugin instances persisted outside the application source tree."""
from __future__ import annotations

import json
import os
import re
import keyring
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

from app.domain.documents import DocumentError


DRIVERS = (
    {"id": "ollama", "name": "Ollama", "category": "llm_providers", "category_name": "LLM",
     "locations": ["local", "network"], "description": "Connect to an Ollama server and discover its installed models.",
     "schema": [
         {"key": "base_url", "label": "Server URL", "type": "text", "required": True,
          "placeholder": "http://192.168.1.25:11434"},
         {"key": "timeout_seconds", "label": "Timeout (seconds)", "type": "number",
          "min": 5, "max": 600, "default": 120}]},
    {"id": "chroma", "name": "Chroma", "category": "vector_stores", "category_name": "Vector Store",
     "locations": ["local"], "description": "Create a separate persistent Chroma vector store.",
     "schema": [
         {"key": "storage_name", "label": "Storage name", "type": "text", "required": True,
          "placeholder": "research-vectors"},
         {"key": "collection_name", "label": "Collection name", "type": "text", "required": True,
          "placeholder": "documents"}]},
    {"id": "qdrant", "name": "Qdrant", "category": "vector_stores", "category_name": "Vector Store",
     "locations": ["local", "network", "cloud"], "description": "Connect to a Qdrant server or Qdrant Cloud cluster.",
     "schema": [
         {"key": "url", "label": "Server URL", "type": "text", "required": True,
          "placeholder": "http://localhost:6333"},
         {"key": "collection_name", "label": "Collection name", "type": "text", "required": True,
          "placeholder": "documents"},
         {"key": "api_key", "label": "API key", "type": "password", "secret": True,
          "placeholder": "Optional for local Qdrant"},
         {"key": "timeout_seconds", "label": "Timeout (seconds)", "type": "number",
          "min": 5, "max": 300, "default": 30}]},
)

_ID = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{1,79}$")
_STORAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,63}$")
_SECRET_SERVICE = "Document Intelligence Plugins"


def _secret_name(plugin_id: str, field: str) -> str:
    return f"{plugin_id}:{field}"


def _secret(plugin_id: str, field: str) -> str | None:
    try:
        return keyring.get_password(_SECRET_SERVICE, _secret_name(plugin_id, field))
    except Exception as error:
        raise DocumentError("CREDENTIAL_STORE_UNAVAILABLE", "The operating system credential store is unavailable.", 503) from error


def _without_secrets(item: dict) -> dict:
    definition = driver(item["driver"], item["category"])
    secret_keys = {field["key"] for field in definition["schema"] if field.get("secret")}
    return {**item, "settings": {key: value for key, value in item["settings"].items() if key not in secret_keys}}


def _save_secrets(item: dict) -> None:
    definition = driver(item["driver"], item["category"])
    try:
        for field in definition["schema"]:
            value = item["settings"].get(field["key"])
            if field.get("secret") and isinstance(value, str) and value:
                keyring.set_password(_SECRET_SERVICE, _secret_name(item["id"], field["key"]), value)
    except Exception as error:
        raise DocumentError("CREDENTIAL_STORE_UNAVAILABLE", "The operating system credential store is unavailable.", 503) from error


def _delete_secrets(item: dict) -> None:
    definition = driver(item["driver"], item["category"])
    for field in definition["schema"]:
        if not field.get("secret"):
            continue
        try:
            keyring.delete_password(_SECRET_SERVICE, _secret_name(item["id"], field["key"]))
        except keyring.errors.PasswordDeleteError:
            pass
        except Exception as error:
            raise DocumentError("CREDENTIAL_STORE_UNAVAILABLE", "The operating system credential store is unavailable.", 503) from error


def driver(driver_id: str, category: str) -> dict:
    found = next((item for item in DRIVERS if item["id"] == driver_id and item["category"] == category), None)
    if found is None:
        raise ValueError(f"Unsupported {category} driver: {driver_id}")
    return found


def validate_instance(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Plugin configuration must be an object")
    allowed = {"id", "name", "category", "driver", "location", "enabled", "settings"}
    if set(value) - allowed:
        raise ValueError("Plugin configuration contains unsupported fields")
    plugin_id, name = value.get("id", ""), value.get("name", "")
    category, driver_id = value.get("category", ""), value.get("driver", "")
    location, enabled, settings = value.get("location", ""), value.get("enabled", True), value.get("settings", {})
    if not isinstance(plugin_id, str) or not _ID.fullmatch(plugin_id):
        raise ValueError("Plugin ID must use 3-64 lowercase letters, numbers, underscores, or hyphens")
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise ValueError("Plugin name is invalid")
    definition = driver(driver_id, category)
    if location not in definition["locations"]:
        raise ValueError(f"{definition['name']} does not support location: {location}")
    if type(enabled) is not bool or not isinstance(settings, dict):
        raise ValueError("Plugin enabled state or settings are invalid")
    schema = {item["key"]: item for item in definition["schema"]}
    if set(settings) - set(schema):
        raise ValueError("Plugin settings contain unsupported fields")
    normalized = {}
    for key, field in schema.items():
        field_value = settings.get(key, field.get("default"))
        if field.get("required") and (field_value is None or field_value == ""):
            raise ValueError(f"{field['label']} is required")
        if field_value is None:
            continue
        if field["type"] == "number":
            if type(field_value) not in (int, float) or not field["min"] <= field_value <= field["max"]:
                raise ValueError(f"{field['label']} is outside its supported range")
        elif not isinstance(field_value, str):
            raise ValueError(f"{field['label']} must be text")
        normalized[key] = field_value
    if driver_id in ("ollama", "qdrant"):
        url_key = "base_url" if driver_id == "ollama" else "url"
        parsed = urlparse(normalized[url_key])
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Server URL must be an HTTP or HTTPS address without embedded credentials")
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("Server URL cannot contain a path, query, or fragment")
        normalized[url_key] = normalized[url_key].rstrip("/")
    if driver_id in ("chroma", "qdrant"):
        names = [normalized["collection_name"]]
        if driver_id == "chroma":
            names.append(normalized["storage_name"])
        if any(not _STORAGE.fullmatch(name) for name in names):
            raise ValueError("Storage and collection names may use letters, numbers, underscores, and hyphens")
    return {"id": plugin_id, "name": name.strip(), "category": category, "driver": driver_id,
            "location": location, "enabled": enabled, "settings": normalized}


class PluginInstanceStore:
    def __init__(self, path: Path):
        self.path = path

    def list(self) -> list[dict]:
        if not self.path.is_file():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("schema_version") != 1 or not isinstance(payload.get("plugins"), list):
                raise ValueError("Unknown plugin configuration format")
            records = [validate_instance(item) for item in payload["plugins"]]
            if len({item["id"] for item in records}) != len(records):
                raise ValueError("Plugin IDs must be unique")
            return records
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise DocumentError("PLUGIN_CONFIG_INVALID", f"Plugin configuration could not be loaded: {error}", 500) from error

    def save_all(self, records: list[dict]) -> None:
        validated = [_without_secrets(validate_instance(item)) for item in records]
        if len({item["id"] for item in validated}) != len(validated):
            raise ValueError("Plugin IDs must be unique")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"schema_version": 1, "plugins": validated}, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

    def create(self, record: dict) -> dict:
        item, records = validate_instance(record), self.list()
        if any(existing["id"] == item["id"] for existing in records):
            raise ValueError(f"Plugin ID already exists: {item['id']}")
        _save_secrets(item)
        item = _without_secrets(item)
        records.append(item)
        self.save_all(records)
        return item

    def update(self, plugin_id: str, record: dict) -> dict:
        item, records = validate_instance({**record, "id": plugin_id}), self.list()
        index = next((i for i, existing in enumerate(records) if existing["id"] == plugin_id), None)
        if index is None:
            raise KeyError(plugin_id)
        if item["category"] != records[index]["category"] or item["driver"] != records[index]["driver"]:
            raise ValueError("Plugin type and driver cannot be changed after creation")
        _save_secrets(item)
        item = _without_secrets(item)
        records[index] = item
        self.save_all(records)
        return item

    def delete(self, plugin_id: str) -> None:
        records = self.list()
        remaining = [item for item in records if item["id"] != plugin_id]
        if len(remaining) == len(records):
            raise KeyError(plugin_id)
        _delete_secrets(next(item for item in records if item["id"] == plugin_id))
        self.save_all(remaining)


def configured_plugin(record: dict, data_dir: Path):
    from app.infrastructure.local_models import ChromaVectorStore
    from app.infrastructure.qdrant_vector_store import QdrantVectorStore
    from app.plugins.ollama_provider import OllamaProvider
    from app.plugins.registry import Plugin

    item = validate_instance(record)
    if item["driver"] == "ollama":
        settings, location = deepcopy(item["settings"]), item["location"]
        return Plugin(item["id"], item["name"], f"{location.title()} Ollama connection.", "llm_providers", (
            {"key": "model", "label": "Model", "type": "model_select"},
            {"key": "temperature", "label": "Temperature", "type": "slider", "min": 0, "max": 1, "step": 0.05},
            {"key": "max_output_tokens", "label": "Maximum output tokens", "type": "number", "min": 64, "max": 4096}),
            {"local": location == "local", "location": location, "driver": "ollama", "model_discovery": True,
             "configured": True},
            lambda _directory=None, values=settings: OllamaProvider(values["base_url"], values["timeout_seconds"]))
    settings = deepcopy(item["settings"])
    if item["driver"] == "qdrant":
        return Plugin(item["id"], item["name"], f"{item['location'].title()} Qdrant connection.", "vector_stores", (
            {"key": "distance", "label": "Distance", "type": "select", "options": ["l2"]},),
            {"local": item["location"] == "local", "location": item["location"], "driver": "qdrant",
             "configured": True},
            lambda _directory=None, profile="standard", values=settings, plugin_id=item["id"]: QdrantVectorStore(
                values["url"], f"{values['collection_name']}_{profile}", _secret(plugin_id, "api_key"),
                values["timeout_seconds"]))
    if item["driver"] != "chroma":
        raise ValueError(f"Unsupported configured plugin driver: {item['driver']}")
    return Plugin(item["id"], item["name"], "Configured local Chroma vector store.", "vector_stores", (
        {"key": "distance", "label": "Distance", "type": "select", "options": ["l2"]},),
        {"local": True, "location": "local", "driver": "chroma", "configured": True},
        lambda _directory=None, profile="standard", values=settings: ChromaVectorStore(
            data_dir / "vectors" / values["storage_name"], f"{values['collection_name']}_{profile}"))


def test_instance(record: dict, data_dir: Path) -> dict:
    item = validate_instance(record)
    plugin = configured_plugin(item, data_dir)
    if item["category"] == "llm_providers":
        provider = plugin.implementation()
        models = provider.models()
        return {"connected": True, "message": f"Ollama {provider.version()}", "resource_count": len(models),
                "resources": models}
    if item["driver"] == "qdrant":
        from app.infrastructure.qdrant_vector_store import QdrantVectorStore
        values = item["settings"]
        store = QdrantVectorStore(values["url"], f"{values['collection_name']}_connection_test",
                                  values.get("api_key") or _secret(item["id"], "api_key"),
                                  values["timeout_seconds"])
        result = store.health_check()
        return {"connected": True, "message": "Qdrant connection is available",
                "resource_count": result["collections"], "resources": []}
    store = plugin.implementation(profile="connection_test")
    store.collection()
    return {"connected": True, "message": "Chroma storage is available", "resource_count": 1,
            "resources": [{"id": store.collection_name, "name": store.collection_name}]}
