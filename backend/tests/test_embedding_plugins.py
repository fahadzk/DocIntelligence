from pathlib import Path
from copy import deepcopy
from uuid import uuid4

from app.application.search import SearchService
from app.config.pipeline_defaults import DEFAULTS
from app.infrastructure.local_models import LocalEmbeddings
from app.infrastructure.search_repository import SearchRepository
from app.plugins.embedding_providers import OllamaEmbeddings, OpenAICompatibleEmbeddings
from app.plugins.registry import Plugin, PluginRegistry


def test_local_embedding_models_are_discovered_from_cache_directory(tmp_path: Path, monkeypatch):
    import fastembed

    class FakeEmbedding:
        @staticmethod
        def list_supported_models():
            return [{"model": "example/model", "sources": {"hf": "vendor/cached-model"}}]

    monkeypatch.setattr(fastembed, "TextEmbedding", FakeEmbedding)
    (tmp_path / "models--vendor--cached-model").mkdir()
    provider = LocalEmbeddings(tmp_path, "example/model")
    assert provider.ready
    assert provider.models() == [{"id": "example/model", "name": "example/model"}]


def test_ollama_embedding_adapter_discovers_and_embeds(monkeypatch):
    provider = OllamaEmbeddings("http://embedding-host:11434", 30, "nomic-embed-text")
    calls = []

    def request(method, path, payload=None):
        calls.append((method, path, payload))
        if path == "/api/tags":
            return {"models": [{"name": "nomic-embed-text"}]}
        return {"embeddings": [[1.0, 2.0], [3.0, 4.0]]}

    monkeypatch.setattr(provider, "_request", request)
    assert provider.models()[0]["id"] == "nomic-embed-text"
    assert provider.embed(["one", "two"]) == [[1.0, 2.0], [3.0, 4.0]]
    assert calls[-1][2] == {"model": "nomic-embed-text", "input": ["one", "two"]}


def test_openai_compatible_embedding_adapter_orders_vectors(monkeypatch):
    provider = OpenAICompatibleEmbeddings("https://example.test/v1", 30, "embed-v1", lambda: "secret")
    monkeypatch.setattr(provider, "_request", lambda method, path, payload=None: {
        "data": [{"index": 1, "embedding": [2.0]}, {"index": 0, "embedding": [1.0]}]
    })
    assert provider.ready
    assert provider.embed(["one", "two"]) == [[1.0], [2.0]]


def test_embedding_plugin_drivers_and_local_instance_api(client):
    drivers = client.get("/api/plugin-drivers").json()["drivers"]
    embedding_drivers = {item["id"] for item in drivers if item["category"] == "embeddings"}
    assert embedding_drivers == {"fastembed", "ollama", "openai_compatible"}

    payload = {
        "id": "research_embeddings",
        "name": "Research embeddings",
        "category": "embeddings",
        "driver": "fastembed",
        "location": "local",
        "enabled": True,
        "settings": {"directory": "models/research-embeddings"},
    }
    created = client.post("/api/plugin-instances", json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["active"] is False
    tested = client.post("/api/plugin-instances/test", json=payload)
    assert tested.status_code == 200, tested.text
    assert tested.json()["message"] == "Local embedding directory is available"


def test_embedding_model_endpoint_lists_app_managed_local_models(client, monkeypatch):
    monkeypatch.setattr(LocalEmbeddings, "models", lambda self: [{"id": "local/model", "name": "local/model"}])
    response = client.get("/api/embedding-providers/fastembed_bge_small/models")
    assert response.status_code == 200, response.text
    assert response.json()["models"] == [
        {"id": "BAAI/bge-small-en-v1.5", "name": "BAAI/bge-small-en-v1.5"},
        {"id": "local/model", "name": "local/model"},
    ]


def test_search_service_resolves_embedding_provider_from_project_config(tmp_path: Path):
    selected = object()
    calls = []

    def factory(data_dir, model):
        calls.append((data_dir, model))
        return selected

    config = deepcopy(DEFAULTS)
    config["document"]["embedding"] = {"plugin": "remote_embeddings", "model": "embed-v2"}

    class Config:
        def effective(self, project_id):
            return config

    class Ready:
        ready = True

    registry = PluginRegistry([
        Plugin("remote_embeddings", "Remote", "Remote embeddings", "embeddings", (), {}, factory),
    ])
    service = SearchService(
        documents=None,
        repository=SearchRepository(tmp_path / "database.sqlite3"),
        data_dir=tmp_path,
        embeddings=Ready(), vectors=object(), llm=Ready(),
        config_service=Config(), registry=registry,
    )
    project_id = uuid4()
    assert service._embeddings_for(project_id) is selected
    assert service._embeddings_for(project_id) is selected
    assert calls == [(tmp_path, "embed-v2")]
