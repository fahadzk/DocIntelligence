"""Pipeline Lab keeps project experiments isolated from the Standard index."""
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor
import threading
import time

from app.config.pipeline_defaults import DEFAULTS, document_version, resolve
from app.plugins.registry import Plugin, PluginRegistry
from app.plugins.strategies import semantic, llm
from app.plugins.cloud_providers import CloudProvider


def project(client, name="Lab"):
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def document(client, project_id, name="notes.txt", text="Europa orbits Jupiter.\n\nJupiter is a planet."):
    response = client.post(f"/api/projects/{project_id}/documents",
                           files=[("files", (name, text.encode(), "text/plain"))])
    assert response.status_code == 200, response.text
    return response.json()[0]["document"]["id"]


def test_plugin_discovery_validation_and_defaults():
    registry = PluginRegistry.discover()
    listed = registry.public()
    assert {item["id"] for item in listed if item["category"] == "chunking"} == {"sliding_window", "semantic", "llm"}
    assert {item["id"] for item in listed if item["category"] == "llm_providers"} == {"llamacpp", "openai", "anthropic", "google"}
    assert registry.get("fusion", "rrf").implementation(0, {"rrf_constant": 40}, "keyword") == 1 / 40
    assert resolve() == DEFAULTS
    assert resolve({"search": {"retrieval": "keyword"}})["search"]["retrieval"] == "keyword"
    assert DEFAULTS["search"]["retrieval"] == "hybrid"
    assert document_version(resolve({"search": {"retrieval": "keyword"}})) == document_version(DEFAULTS)
    first = Plugin("x", "X", "X", "fusion", (), {}, lambda: None)
    try:
        PluginRegistry([first, first])
        assert False, "duplicate plugin must be rejected"
    except ValueError:
        pass
    try:
        PluginRegistry([Plugin("broken", "Broken", "Broken", "fusion")])
        assert False, "plugin without implementation must be rejected"
    except ValueError:
        pass


def test_project_overrides_preview_search_and_standard_isolation(client):
    first = project(client, "First")
    second = project(client, "Second")
    doc = document(client, first, text=("Europa orbits Jupiter. " * 45) + "\n\nA second paragraph names Ganymede.")
    from app.main import get_search_service
    get_search_service().ensure_indexes()
    standard_before = client.post(f"/api/projects/{first}/search", json={"query": "Europa"}).json()["results"]
    assert standard_before
    registry = client.get("/api/plugins").json()["plugins"]
    assert any(item["id"] == "semantic" and item["category"] == "chunking" for item in registry)
    state = client.get(f"/api/projects/{first}/pipeline").json()
    assert state["effective"]["document"]["chunking"]["chunk_size"] == 900
    changed = client.put(f"/api/projects/{first}/pipeline", json={"overrides": {
        "document": {"chunking": {"chunk_size": 300, "overlap": 50}},
        "search": {"retrieval": "keyword", "result_limit": 5}}})
    assert changed.status_code == 200, changed.text
    assert client.get(f"/api/projects/{second}/pipeline").json()["effective"]["document"]["chunking"]["chunk_size"] == 900
    preview = client.post(f"/api/projects/{first}/pipeline/preview", json={"document_id": doc}).json()
    assert preview["count"] > 1
    assert preview["samples"][0]["label"] == "Paragraph 1"
    from app.main import get_lab_search_service
    get_lab_search_service().ensure_project(UUID(first))
    found = client.post(f"/api/projects/{first}/pipeline/search", json={"query": "Europa"})
    assert found.status_code == 200, found.text
    assert found.json()["results"][0]["document_id"] == doc
    assert found.json()["results"][0]["keyword_rank"] == 1
    assert client.post(f"/api/projects/{second}/pipeline/search", json={"query": "Europa"}).json()["results"] == []
    standard_after = client.post(f"/api/projects/{first}/search", json={"query": "Europa"}).json()["results"]
    assert [item["id"] for item in standard_after] == [item["id"] for item in standard_before]
    assert client.delete(f"/api/projects/{first}/documents/{doc}").status_code == 204
    assert client.post(f"/api/projects/{first}/pipeline/search", json={"query": "Europa"}).json()["results"] == []


def test_invalid_plugin_and_settings_are_rejected(client):
    pid = project(client)
    bad = client.put(f"/api/projects/{pid}/pipeline", json={"overrides": {"document": {"chunking": {"plugin": "missing"}}}})
    assert bad.status_code == 422
    bad = client.put(f"/api/projects/{pid}/pipeline", json={"overrides": {"document": {"chunking": {"chunk_size": 100, "overlap": 120}}}})
    assert bad.status_code == 422
    assert client.get(f"/api/projects/{pid}/pipeline").json()["overrides"] == {}


def test_semantic_and_llm_chunkers_preserve_offsets():
    segments = [{"index": 0, "text": "First topic.\n\nSecond subject.\n\nThird subject.",
                 "label": "Page 2", "page_number": 2, "paragraph_number": None}]
    class Embeddings:
        ready = True
        def embed(self, texts):
            return [[1.0, 0.0], [0.0, 1.0], [0.0, 1.0]]
    settings = {"sensitivity": 0.5, "min_chunk_size": 1, "max_chunk_size": 100}
    chunks = semantic("p", "d", "hash", segments, "v", settings, embeddings=Embeddings())
    assert len(chunks) == 2
    assert all(item["page_number"] == 2 for item in chunks)
    assert all(segments[0]["text"][item["start_offset"]:item["end_offset"]].strip() == item["text"] for item in chunks)
    class Model:
        ready = True
        def answer(self, _system, _prompt):
            return "[1]"
    chunks = llm("p", "d", "hash", segments, "v", {"chunk_by": "topic", "max_chunk_size": 100}, llm=Model())
    assert len(chunks) == 2


def test_lab_ask_returns_real_context_and_citations(client):
    pid = project(client)
    doc = document(client, pid, text="Europa orbits Jupiter.")
    from app.main import get_lab_search_service
    lab = get_lab_search_service()
    lab.ensure_project(UUID(pid))
    class Model:
        ready = True
        def answer(self, system, prompt, options):
            assert "Europa orbits Jupiter" in prompt
            assert options["temperature"] == 0.0
            return "Europa orbits Jupiter [1]."
    lab.llm = Model()
    response = client.post(f"/api/projects/{pid}/pipeline/ask", json={"question": "What does Europa orbit?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["supported"]
    assert body["evidence"][0]["passage"]["document_id"] == doc
    assert body["context"][0]["chunk_id"] == body["evidence"][0]["passage"]["id"]
    assert body["context"][0]["text"] == "Europa orbits Jupiter."


def test_cloud_credentials_never_return_secret(monkeypatch):
    saved = {}
    import app.plugins.cloud_providers as providers
    monkeypatch.setattr(providers.keyring, "set_password", lambda service, name, value: saved.__setitem__(name, value))
    monkeypatch.setattr(providers.keyring, "get_password", lambda service, name: saved.get(name))
    cloud = CloudProvider("openai")
    cloud.save_credential("secret-value")
    assert cloud.configured()
    assert "secret-value" not in repr({"configured": cloud.configured()})
    monkeypatch.setattr(cloud, "_request", lambda method, path, payload=None: {"data": [{"id": "discovered-model"}]})
    assert cloud.models() == [{"id": "discovered-model", "name": "discovered-model"}]


def test_semantic_hybrid_weighted_and_optional_reranking(client):
    pid = project(client, "Retrieval")
    europa = document(client, pid, "europa.txt", "Europa orbits Jupiter.")
    ganymede = document(client, pid, "ganymede.txt", "Ganymede orbits Jupiter.")
    from app.main import get_lab_search_service, get_pipeline_config
    lab = get_lab_search_service()
    lab.ensure_project(UUID(pid))

    class Embeddings:
        ready = True
        def embed(self, texts):
            return [[1.0, 0.0] for _ in texts]

    class Vectors:
        def __init__(self):
            self.rows = {}
        def delete(self, project_id, document_id):
            self.rows.pop(document_id, None)
        def upsert(self, ids, texts, vectors, project_id, document_id):
            self.rows[document_id] = ids
        def search_with_distances(self, project_id, vector, limit):
            return [(self.rows[ganymede][0], 0.1), (self.rows[europa][0], 0.3)][:limit]

    lab.embeddings = Embeddings()
    lab.vectors = Vectors()
    lab.index_document(UUID(pid), UUID(europa), force=True)
    lab.index_document(UUID(pid), UUID(ganymede), force=True)
    config = get_pipeline_config()
    config.save(UUID(pid), {"search": {"retrieval": "semantic", "similarity_threshold": 0.2}})
    semantic_results = lab.search(UUID(pid), "Europa")
    assert len(semantic_results) == 1
    assert semantic_results[0]["document_id"] == ganymede
    assert semantic_results[0]["semantic_score"] == 0.1
    config.save(UUID(pid), {"search": {"retrieval": "hybrid", "fusion": "weighted",
                                            "keyword_weight": 0.8, "semantic_weight": 0.2,
                                            "similarity_threshold": None, "reranker": "lexical"}})
    hybrid = lab.search(UUID(pid), "Europa")
    assert hybrid[0]["document_id"] == europa
    assert hybrid[0]["keyword_rank"] == 1
    assert hybrid[0]["semantic_rank"] == 2
    assert hybrid[0]["reranker_score"] >= hybrid[1]["reranker_score"]


def test_provider_api_never_echoes_credential(client, monkeypatch):
    import app.plugins.cloud_providers as providers
    saved = {}
    monkeypatch.setattr(providers.keyring, "set_password", lambda service, name, key: saved.__setitem__(name, key))
    monkeypatch.setattr(providers.keyring, "get_password", lambda service, name: saved.get(name))
    response = client.put("/api/providers/openai/credential", json={"key": "private-test-key"})
    assert response.status_code == 200
    assert "private-test-key" not in response.text
    assert client.get("/api/providers").json()[0] == {"id": "openai", "configured": True}


def test_lab_grounding_modes_keep_document_citations_valid(client):
    pid = project(client, "Grounding")
    document(client, pid, text="Europa orbits Jupiter.")
    from app.main import get_lab_search_service, get_pipeline_config
    lab = get_lab_search_service()
    lab.ensure_project(UUID(pid))
    class Model:
        ready = True
        def answer(self, system, prompt, options):
            return ("Europa orbits Jupiter [1].\n\n"
                    "Model knowledge (not verified by documents): Europa is an icy moon.")
    lab.llm = Model()
    get_pipeline_config().save(UUID(pid), {"ask": {"grounding": "sources_plus_model",
                                                 "require_citations": False}})
    response = client.post(f"/api/projects/{pid}/pipeline/ask", json={"question": "What does Europa orbit?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["supported"]
    assert "[1]" not in body["answer"]
    assert body["evidence"][0]["passage"]["document_id"]
    assert body["background"] == "Europa is an icy moon."


def test_standard_and_lab_serialize_chroma_collection_initialization(tmp_path, monkeypatch):
    import chromadb
    from app.infrastructure.local_models import ChromaVectorStore

    gate = threading.Lock()
    active = 0
    peak = 0

    class FakeClient:
        def get_or_create_collection(self, name):
            return name

    def persistent_client(path):
        nonlocal active, peak
        with gate:
            active += 1
            peak = max(peak, active)
        time.sleep(0.05)
        with gate:
            active -= 1
        return FakeClient()

    monkeypatch.setattr(chromadb, "PersistentClient", persistent_client)
    stores = [ChromaVectorStore(tmp_path / "vectors", "standard"),
              ChromaVectorStore(tmp_path / "vectors", "pipeline_lab")]
    with ThreadPoolExecutor(max_workers=2) as pool:
        names = list(pool.map(lambda store: store.collection(), stores))
    assert names == ["standard", "pipeline_lab"]
    assert peak == 1


def test_shared_local_embedding_model_runs_one_job_at_a_time(tmp_path, monkeypatch):
    import fastembed
    from app.infrastructure.local_models import LocalEmbeddings

    (tmp_path / "ready").touch()
    gate = threading.Lock()
    active = 0
    peak = 0
    initialized = 0

    class Vector:
        def tolist(self):
            return [1.0]

    class FakeEmbedding:
        def __init__(self, **kwargs):
            nonlocal initialized
            initialized += 1

        def embed(self, texts):
            nonlocal active, peak
            with gate:
                active += 1
                peak = max(peak, active)
            time.sleep(0.05)
            with gate:
                active -= 1
            return [Vector() for _ in texts]

    monkeypatch.setattr(fastembed, "TextEmbedding", FakeEmbedding)
    provider = LocalEmbeddings(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(lambda _: provider.embed(["text"]), range(2)))
    assert values == [[[1.0]], [[1.0]]]
    assert initialized == 1
    assert peak == 1
