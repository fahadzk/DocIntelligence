"""Optional, app-managed CPU models. No hosted inference calls."""
from pathlib import Path
import threading
from typing import Protocol
from app.config.pipeline_defaults import DEFAULTS


EMBED_MODEL = DEFAULTS["document"]["embedding"]["model"]
LLM_REPOSITORY = DEFAULTS["ask"]["model_repository"]
LLM_FILENAME = DEFAULTS["ask"]["model"]


class InsufficientMemoryError(RuntimeError):
    pass


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LLMProvider(Protocol):
    def answer(self, system: str, prompt: str) -> str: ...


class LocalEmbeddings:
    def __init__(self, directory: Path):
        self.directory = directory
        self._model = None
        self._embedding_lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return (self.directory / "ready").is_file()

    def provision(self) -> None:
        from fastembed import TextEmbedding
        self.directory.mkdir(parents=True, exist_ok=True)
        self._model = TextEmbedding(model_name=EMBED_MODEL, cache_dir=str(self.directory),
                                    threads=2, local_files_only=False)
        (self.directory / "ready").touch()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.ready:
            raise RuntimeError("The semantic search model has not been downloaded.")
        with self._embedding_lock:
            if self._model is None:
                from fastembed import TextEmbedding
                self._model = TextEmbedding(model_name=EMBED_MODEL, cache_dir=str(self.directory),
                                            threads=2, local_files_only=True)
            return [vector.tolist() for vector in self._model.embed(texts)]


class LocalLLM:
    def __init__(self, directory: Path):
        self.directory = directory
        self._generation_lock = threading.Lock()
        self.path = directory / LLM_FILENAME
        self._model = None

    @property
    def ready(self) -> bool:
        return self.path.is_file() and self.path.stat().st_size > 900_000_000

    def provision(self) -> None:
        from huggingface_hub import hf_hub_download
        self.directory.mkdir(parents=True, exist_ok=True)
        hf_hub_download(repo_id=LLM_REPOSITORY, filename=LLM_FILENAME,
                        local_dir=self.directory)
        if not self.ready:
            raise RuntimeError("The downloaded answer model is incomplete.")

    def answer(self, system: str, prompt: str, options: dict | None = None) -> str:
        with self._generation_lock:
            return self._answer(system, prompt, options)

    def _answer(self, system: str, prompt: str, options: dict | None = None) -> str:
        if not self.ready:
            raise RuntimeError("The answer model has not been downloaded.")
        if self._model is None:
            import psutil
            if psutil.virtual_memory().available < DEFAULTS["ask"]["minimum_free_bytes"]:
                raise InsufficientMemoryError("At least 2.5 GB of free memory is needed to load the local answer model. Close other applications and try again; Search remains available.")
            from llama_cpp import Llama
            self._model = Llama(model_path=str(self.path), n_ctx=(options or {}).get("context_tokens", DEFAULTS["ask"]["context_tokens"]),
                                n_threads=DEFAULTS["ask"]["threads"], n_gpu_layers=DEFAULTS["ask"]["gpu_layers"],
                                chat_format=DEFAULTS["ask"]["chat_format"], verbose=False)
        self._model.reset()
        response = self._model.create_chat_completion(
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt}],
            temperature=(options or {}).get("temperature", DEFAULTS["ask"]["temperature"]),
            max_tokens=(options or {}).get("max_output_tokens", DEFAULTS["ask"]["max_output_tokens"]),
            seed=(options or {}).get("seed", DEFAULTS["ask"]["seed"]))
        return str(response["choices"][0]["message"]["content"] or "")


class VectorStore(Protocol):
    def upsert(self, ids: list[str], texts: list[str], vectors: list[list[float]],
               project_id: str, document_id: str) -> None: ...
    def search(self, project_id: str, vector: list[float], limit: int) -> list[str]: ...
    def delete(self, project_id: str, document_id: str) -> None: ...


class ChromaVectorStore:
    # Chroma maintains a process-wide client registry per persistence path. Creating
    # Standard and Lab collections concurrently can race that registry on Windows.
    _client_lock = threading.Lock()

    def __init__(self, directory: Path, collection_name: str = "bge_small_en_v15_chunk_v1"):
        self.directory = directory
        self.collection_name = collection_name
        self._collection = None

    def collection(self):
        if self._collection is None:
            with self._client_lock:
                if self._collection is None:
                    import chromadb
                    self.directory.mkdir(parents=True, exist_ok=True)
                    client = chromadb.PersistentClient(path=str(self.directory))
                    self._collection = client.get_or_create_collection(self.collection_name)
        return self._collection

    def upsert(self, ids: list[str], texts: list[str], vectors: list[list[float]],
               project_id: str, document_id: str) -> None:
        self.delete(project_id, document_id)
        if ids:
            self.collection().upsert(ids=ids, documents=texts, embeddings=vectors,
                                     metadatas=[{"project_id": project_id, "document_id": document_id}
                                                for _ in ids])

    def search(self, project_id: str, vector: list[float], limit: int) -> list[str]:
        result = self.collection().query(query_embeddings=[vector], n_results=limit,
                                          where={"project_id": project_id}, include=[])
        return result["ids"][0]

    def search_with_distances(self, project_id: str, vector: list[float], limit: int) -> list[tuple[str, float]]:
        result = self.collection().query(query_embeddings=[vector], n_results=limit,
                                         where={"project_id": project_id}, include=["distances"])
        return list(zip(result["ids"][0], result["distances"][0]))

    def delete(self, project_id: str, document_id: str) -> None:
        self.collection().delete(where={"$and": [{"project_id": project_id},
                                                   {"document_id": document_id}]})
