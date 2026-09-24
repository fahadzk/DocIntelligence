from uuid import UUID
import time
import fitz

from app.main import get_search_service
from app.infrastructure.local_models import InsufficientMemoryError


def make_project(client, name):
    return client.post("/api/projects", json={"name": name}).json()["id"]


def add(client, project_id, name, text):
    result = client.post(
        f"/api/projects/{project_id}/documents",
        files=[("files", (name, text.encode("utf-8"), "text/plain"))],
    )
    assert result.status_code == 200, result.text
    document_id = result.json()[0]["document"]["id"]
    for _ in range(100):
        states = client.get(f"/api/projects/{project_id}/index/status").json()
        if any(item["document_id"] == document_id and item["status"] == "ready" for item in states):
            break
        time.sleep(0.05)
    assert any(item["document_id"] == document_id and item["status"] == "ready" for item in states)
    return document_id


def test_keyword_index_evidence_isolation_and_deletion(client):
    service = get_search_service()
    first = make_project(client, "One")
    second = make_project(client, "Two")
    one = add(client, first, "orbit.txt", "The telescope observed Europa orbiting Jupiter.")
    two = add(client, second, "secret.txt", "The private telescope is in another project.")
    found = client.post(f"/api/projects/{first}/search", json={"query": "telescope"}).json()["results"]
    assert len(found) == 1
    assert found[0]["document_id"] == one
    assert found[0]["paragraph_number"] == 1
    assert found[0]["match_type"] == "keyword"
    evidence_id = found[0]["id"]
    assert client.get(f"/api/projects/{first}/evidence/{evidence_id}").status_code == 200
    assert client.get(f"/api/projects/{second}/evidence/{evidence_id}").status_code == 404
    assert client.delete(f"/api/projects/{first}/documents/{one}").status_code == 204
    assert client.post(f"/api/projects/{first}/search", json={"query": "telescope"}).json()["results"] == []
    assert client.get(f"/api/projects/{first}/evidence/{evidence_id}").status_code == 404
    assert client.get(f"/api/projects/{second}/documents/{two}").status_code == 200
    assert service.repository.valid_ids(first) == set()


def test_answer_citations_are_validated(client):
    first = make_project(client, "Answers")
    add(client, first, "facts.txt", "Europa orbits Jupiter.")
    service = get_search_service()

    class FakeLLM:
        ready = True
        def answer(self, system, prompt):
            assert "untrusted data" in system
            assert "Europa orbits Jupiter" in prompt
            return "Europa orbits Jupiter [1]."

    service.llm = FakeLLM()
    response = client.post(f"/api/projects/{first}/ask", json={"question": "What does Europa orbit?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["supported"]
    assert len(body["evidence"]) == 1
    assert body["evidence"][0]["passage"]["project_id"] == first

    class ParagraphCitedLLM:
        ready = True
        def answer(self, _system, _prompt):
            return "Europa orbits Jupiter, according to the document [1]."

    service.llm = ParagraphCitedLLM()
    body = client.post(f"/api/projects/{first}/ask", json={"question": "What does Europa orbit?"}).json()
    assert body["supported"]
    assert body["evidence"][0]["number"] == 1

    class UnmarkedButGroundedLLM:
        ready = True
        def answer(self, _system, _prompt):
            return "Europa orbits Jupiter, according to the retrieved document. [1]"

    service.llm = UnmarkedButGroundedLLM()
    body = client.post(f"/api/projects/{first}/ask", json={"question": "What does Europa orbit?"}).json()
    assert body["supported"]
    assert body["answer"].endswith("[1]")
    assert body["evidence"][0]["number"] == 1

    class HallucinatedLLM:
        ready = True
        def answer(self, _system, _prompt):
            return "Europa is a moon of Mars and its capital is Olympus."

    service.llm = HallucinatedLLM()
    body = client.post(f"/api/projects/{first}/ask", json={"question": "What does Europa orbit?"}).json()
    assert not body["supported"]
    assert body["evidence"] == []
    class InvalidLLM:
        ready = True
        def answer(self, _system, _prompt):
            return "Unsupported claim [9]."

    service.llm = InvalidLLM()
    body = client.post(f"/api/projects/{first}/ask", json={"question": "What does Europa orbit?"}).json()
    assert not body["supported"]
    assert body["evidence"] == []

    class PartlyUncitedLLM:
        ready = True
        def answer(self, _system, _prompt):
            return "Europa orbits Jupiter [1]. An unrelated assertion."

    service.llm = PartlyUncitedLLM()
    body = client.post(f"/api/projects/{first}/ask", json={"question": "What does Europa orbit?"}).json()
    assert not body["supported"]

    class LowMemoryLLM:
        ready = True
        def answer(self, _system, _prompt):
            raise InsufficientMemoryError("At least 2.5 GB of free memory is needed.")

    service.llm = LowMemoryLLM()
    response = client.post(f"/api/projects/{first}/ask", json={"question": "What does Europa orbit?"})
    assert response.status_code == 503
    assert response.json()["code"] == "MODEL_MEMORY_LOW"


def test_index_rebuild_after_restart(client):
    first = make_project(client, "Restart")
    document_id = add(client, first, "persist.txt", "Persistent indexed passage.")
    service = get_search_service()
    service.repository.mark(first, document_id, "indexing", "embedding", "old-version", "old-hash")
    service.ensure_indexes()
    status = client.get(f"/api/projects/{first}/index/status").json()[0]
    assert status["status"] == "ready"
    assert status["index_version"] == service.version
    found = client.post(f"/api/projects/{first}/search", json={"query": "Persistent"}).json()["results"]
    assert found[0]["document_id"] == document_id
    assert UUID(found[0]["id"])


def test_pdf_page_evidence_and_scanned_exclusion(client):
    project = make_project(client, "Sources")
    pdf = fitz.open()
    pdf.new_page().insert_text((72, 72), "Unrelated first page.")
    pdf.new_page().insert_text((72, 72), "The observatory catalogued a comet.")
    contents = pdf.tobytes()
    pdf.close()
    result = client.post(f"/api/projects/{project}/documents",
        files=[("files", ("report.pdf", contents, "application/pdf"))])
    assert result.status_code == 200
    get_search_service().ensure_indexes()
    found = client.post(f"/api/projects/{project}/search",
        json={"query": "comet"}).json()["results"]
    assert found[0]["page_number"] == 2
    assert found[0]["label"] == "Page 2"
    assert client.get(f"/api/projects/{project}/documents/{found[0]['document_id']}/original").content == contents
    blank = fitz.open()
    blank.new_page()
    scanned = blank.tobytes()
    blank.close()
    failed = client.post(f"/api/projects/{project}/documents",
        files=[("files", ("scan.pdf", scanned, "application/pdf"))]).json()[0]["document"]
    assert client.get(f"/api/projects/{project}/documents/{failed['id']}").json()["error_code"] == "NO_EXTRACTABLE_TEXT"
    assert not any(item["document_id"] == failed["id"] for item in found)


def test_keyword_index_can_be_rebuilt(client):
    project = make_project(client, "Rebuild")
    add(client, project, "recover.txt", "Rebuildable source text.")
    service = get_search_service()
    with service.repository.connect() as connection:
        connection.execute("DROP TABLE passages_fts")
    failed = client.post(f"/api/projects/{project}/search", json={"query": "Rebuildable"})
    assert failed.status_code == 503
    assert failed.json()["code"] == "INDEX_UNAVAILABLE"
    assert client.post(f"/api/projects/{project}/index/rebuild").status_code == 200
    for _ in range(40):
        recovered = client.post(f"/api/projects/{project}/search", json={"query": "Rebuildable"})
        if recovered.status_code == 200 and recovered.json()["results"]:
            break
        time.sleep(0.1)
    assert recovered.status_code == 200
    assert recovered.json()["results"]


def test_repair_attempt_does_not_replace_generated_answer_with_quote(client):
    project = make_project(client, "Repair")
    add(client, project, "facts.txt", "Europa orbits Jupiter.")
    service = get_search_service()

    class RepairLLM:
        ready = True
        calls = 0

        def answer(self, system, prompt):
            self.calls += 1
            if self.calls == 1:
                return "Europa orbits Mars [1]."
            assert "unsupported_claim" in prompt
            return "Europa orbits Jupiter. [1]"

    model = RepairLLM()
    service.llm = model
    response = service.ask(UUID(project), "Which planet does Europa orbit?")
    assert model.calls == 2
    assert response["answer"] == "Europa orbits Jupiter. [1]"
    assert response["supported"]
