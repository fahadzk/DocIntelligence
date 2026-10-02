from pathlib import Path

import pytest

from app.infrastructure.neo4j_vector_store import Neo4jVectorStore
from app.plugins.instances import configured_plugin, validate_instance


def neo4j_record() -> dict:
    return {
        "id": "research_graph",
        "name": "Research graph",
        "category": "vector_stores",
        "driver": "neo4j",
        "location": "network",
        "enabled": True,
        "settings": {
            "uri": "neo4j://graph.internal:7687",
            "database": "neo4j",
            "username": "neo4j",
            "password": "secret",
            "index_name": "document_vectors",
            "dimensions": 3,
            "timeout_seconds": 30,
        },
    }


def test_neo4j_plugin_configuration_builds_network_store(tmp_path: Path):
    record = validate_instance(neo4j_record())
    plugin = configured_plugin(record, tmp_path)
    store = plugin.implementation(tmp_path, profile="standard_abc")
    assert plugin.category == "vector_stores"
    assert plugin.capabilities["location"] == "network"
    assert store.uri == "neo4j://graph.internal:7687"
    assert store.index_name == "document_vectors_standard_abc"
    assert store.dimensions == 3


def test_neo4j_upsert_keeps_chunk_text_local(monkeypatch):
    store = Neo4jVectorStore("neo4j://graph:7687", "neo4j", "neo4j", "secret", "vectors", dimensions=3)
    calls = []
    monkeypatch.setattr(store, "ensure_index", lambda project_id: "ONLINE")
    monkeypatch.setattr(store, "_execute", lambda query, **parameters: calls.append((query, parameters)) or [])
    store.upsert(["passage-1"], ["private chunk text"], [[0.1, 0.2, 0.3]], "project-1", "document-1")
    query, parameters = calls[1]
    assert all("private chunk text" not in statement for statement, _parameters in calls)
    assert parameters["rows"] == [{"id": "passage-1", "embedding": [0.1, 0.2, 0.3]}]
    assert set(parameters) == {"project_id", "document_id", "rows"}


def test_neo4j_creates_project_isolated_vector_index(monkeypatch):
    store = Neo4jVectorStore("neo4j://graph:7687", "neo4j", "neo4j", "secret", "vectors", dimensions=3)
    calls = []
    index, label = store._scope("project-1")

    def execute(query, **parameters):
        calls.append((query, parameters))
        if query.startswith("SHOW VECTOR INDEXES"):
            return [{"label": label, "property": "embedding", "dimensions": 3,
                     "similarity": "euclidean", "state": "ONLINE"}]
        return []

    monkeypatch.setattr(store, "_execute", execute)
    assert store.ensure_index("project-1") == "ONLINE"
    assert f"CREATE VECTOR INDEX `{index}`" in calls[0][0]
    assert f"FOR (node:`{label}`)" in calls[0][0]
    assert store._scope("project-2") != (index, label)


def test_neo4j_search_returns_ids_and_normalized_distances(monkeypatch):
    store = Neo4jVectorStore("neo4j://graph:7687", "neo4j", "neo4j", "secret", "vectors", dimensions=3)
    monkeypatch.setattr(store, "ensure_index", lambda project_id: "ONLINE")
    monkeypatch.setattr(store, "_execute", lambda query, **parameters: [
        {"id": "passage-1", "score": 0.9}, {"id": "passage-2", "score": 0.6}
    ])
    results = store.search_with_distances("project-1", [0.1, 0.2, 0.3], 2)
    assert [item[0] for item in results] == ["passage-1", "passage-2"]
    assert [item[1] for item in results] == pytest.approx([0.1, 0.4])


def test_neo4j_driver_is_available_in_plugin_api(client):
    drivers = client.get("/api/plugin-drivers").json()["drivers"]
    neo4j = next(item for item in drivers if item["category"] == "vector_stores" and item["id"] == "neo4j")
    assert neo4j["locations"] == ["network", "cloud"]
    assert {field["key"] for field in neo4j["schema"]} >= {
        "uri", "database", "username", "password", "index_name", "dimensions"
    }
