"""Offline smoke benchmark using installed models and disposable project data."""
import os
import sys
import tempfile
import time
import gc
import argparse
import logging
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["HF_HUB_OFFLINE"] = "1"

from fastapi.testclient import TestClient  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.infrastructure.local_models import LocalEmbeddings, LocalLLM, ChromaVectorStore  # noqa: E402
from app.main import app, get_document_service, get_project_service, get_search_service  # noqa: E402

logging.getLogger("httpx").setLevel(logging.WARNING)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", action="store_true", help="also load and benchmark the local answer model")
    options = parser.parse_args()
    models = ROOT / "data" / "models"
    embedding = LocalEmbeddings(models / "embeddings")
    if not embedding.ready:
        raise SystemExit("Set up semantic search in the app before running this benchmark.")
    with tempfile.TemporaryDirectory(prefix="document-intelligence-phase3-") as directory:
        os.environ["DOCUMENT_INTELLIGENCE_DATA_DIR"] = directory
        for cache in (get_settings, get_project_service, get_document_service, get_search_service):
            cache.cache_clear()
        with TestClient(app) as client:
            search = get_search_service()
            search.embeddings = embedding
            search.vectors = ChromaVectorStore(Path(directory) / "vectors")
            llm = LocalLLM(models / "answers")
            search.llm = llm
            project = client.post("/api/projects", json={"name": "Offline verification"}).json()["id"]
            fixtures = [
                ("science.txt", b"Europa is a moon of Jupiter. It orbits the giant planet every 3.5 days."),
                ("history.md", b"# Expedition\n\nThe expedition started in 1842 and mapped the northern coast."),
                ("finance.txt", b"The 2025 revenue was 12 million dollars."),
            ]
            start = time.perf_counter()
            for filename, contents in fixtures:
                response = client.post(f"/api/projects/{project}/documents",
                    files=[("files", (filename, contents, "text/plain"))])
                assert response.status_code == 200, response.text
                assert response.json()[0]["document"]["id"]
            for _ in range(600):
                states = client.get(f"/api/projects/{project}/index/status").json()
                if len(states) == 3 and all(item["status"] == "ready" for item in states):
                    break
                time.sleep(0.1)
            assert len(states) == 3 and all(item["status"] == "ready" for item in states)
            print(f"Indexed three small documents: {time.perf_counter() - start:.2f}s")
            start = time.perf_counter()
            results = client.post(f"/api/projects/{project}/search",
                json={"query": "Which satellite circles the gas giant?"}).json()["results"]
            print(f"Offline paraphrase search: {time.perf_counter() - start:.2f}s")
            for item in results[:3]:
                print(f"  {item['display_name']}: {item['text'][:90]}")
            assert results and results[0]["display_name"] == "science.txt"
            if llm.ready and options.answers:
                start = time.perf_counter()
                answer = client.post(f"/api/projects/{project}/ask",
                    json={"question": "Which planet does Europa orbit?"}).json()
                print(f"Offline answer: {time.perf_counter() - start:.2f}s")
                print(answer)
                assert answer["supported"] and answer["evidence"]
                assert answer["evidence"][0]["passage"]["project_id"] == project
                unknown = client.post(f"/api/projects/{project}/ask",
                    json={"question": "Who was the mayor of Atlantis in 2030?"}).json()
                print(f"Unsupported question: {unknown}")
                assert not unknown["supported"]
            else:
                print("Ask benchmark skipped; use --answers after installing the answer model.")
        for worker in threading.enumerate():
            if worker.name.startswith("index-"):
                worker.join(timeout=30)
        documents = get_document_service()
        documents.on_ready = None
        documents.on_delete = None
        for cache in (get_settings, get_project_service, get_document_service, get_search_service):
            cache.cache_clear()
        search.vectors._collection = None
        del search
        del documents
        gc.collect()
        from chromadb.api.client import SharedSystemClient
        for system in SharedSystemClient._identifier_to_system.values():
            system.stop()
        SharedSystemClient.clear_system_cache()
        gc.collect()


if __name__ == "__main__":
    main()
