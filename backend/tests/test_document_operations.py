import time
from uuid import UUID

from app.domain.documents import DocumentError
from app.main import get_search_service


def make_project(client, name):
    return client.post("/api/projects", json={"name": name}).json()["id"]


def add(client, project_id, name, text):
    response = client.post(
        f"/api/projects/{project_id}/documents",
        files=[("files", (name, text.encode("utf-8"), "text/plain"))],
    )
    document_id = response.json()[0]["document"]["id"]
    for _ in range(100):
        states = client.get(f"/api/projects/{project_id}/index/status").json()
        if any(item["document_id"] == document_id and item["status"] == "ready" for item in states):
            return document_id
        time.sleep(0.05)
    raise AssertionError("Document index did not become ready")


def test_rechunk_and_reembed_are_independent_operations(client):
    project = make_project(client, "Independent operations")
    document_id = add(client, project, "source.txt", "One paragraph.\n\nA second paragraph.")
    service = get_search_service()

    class Embeddings:
        ready = True
        calls = 0

        def embed(self, texts):
            self.calls += 1
            return [[1.0, 0.0] for _ in texts]

    class Vectors:
        deleted = 0
        upserted = 0

        def delete(self, project_id, selected_document_id):
            assert project_id == project
            assert selected_document_id == document_id
            self.deleted += 1

        def upsert(self, ids, texts, vectors, project_id, selected_document_id):
            self.upserted += 1

    embeddings, vectors = Embeddings(), Vectors()
    service.embeddings, service.vectors = embeddings, vectors

    service.rechunk_document(UUID(project), UUID(document_id))
    assert embeddings.calls == 0
    assert vectors.deleted == 1
    assert vectors.upserted == 0
    assert client.get(f"/api/projects/{project}/index/status").json()[0]["stage"] == "chunked"

    service.reembed_document(UUID(project), UUID(document_id))
    assert embeddings.calls == 1
    assert vectors.upserted == 1
    assert client.get(f"/api/projects/{project}/index/status").json()[0]["stage"] == "complete"


def test_reembed_failure_is_persisted_without_triggering_rechunk(client, monkeypatch):
    project = make_project(client, "Embedding failure")
    document_id = add(client, project, "source.txt", "Existing chunks stay unchanged.")
    service = get_search_service()

    class FailingEmbeddings:
        ready = True

        def embed(self, texts):
            raise DocumentError(
                "EMBEDDING_PROVIDER_UNAVAILABLE",
                "Could not reach the embedding provider",
                503,
            )

    service.embeddings = FailingEmbeddings()
    monkeypatch.setattr(
        service,
        "rechunk_document",
        lambda *_: (_ for _ in ()).throw(AssertionError("must not re-chunk")),
    )

    service.reembed_document(UUID(project), UUID(document_id))
    status = client.get(f"/api/projects/{project}/index/status").json()[0]
    assert status["status"] == "ready"
    assert status["stage"] == "re-embedding_failed"
    assert status["error_message"] == (
        "Re-embedding failed due to: Could not reach the embedding provider. "
        "Check the server log for details."
    )


def test_startup_recovery_does_not_retry_a_failed_index(client, monkeypatch):
    project = make_project(client, "No silent retry")
    document_id = add(client, project, "source.txt", "Do not restart failed embedding work.")
    service = get_search_service()
    document = service.documents.get(UUID(project), UUID(document_id))
    service.repository.mark(
        project,
        document_id,
        "failed",
        "embedding",
        service.version_for(UUID(project)),
        document.content_hash,
        "Embedding failed.",
    )
    calls = []
    monkeypatch.setattr(service, "index_document", lambda *args, **kwargs: calls.append((args, kwargs)))

    service.ensure_indexes()

    assert calls == []
