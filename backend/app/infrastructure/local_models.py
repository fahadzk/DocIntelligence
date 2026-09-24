"""Optional, app-managed CPU models. No hosted inference calls."""
from pathlib import Path
import threading
from typing import Protocol


EMBED_MODEL = "BAAI/bge-small-en-v1.5"
LLM_REPOSITORY = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
LLM_FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"


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

    def answer(self, system: str, prompt: str) -> str:
        with self._generation_lock:
            return self._answer(system, prompt)

    def _answer(self, system: str, prompt: str) -> str:
        if not self.ready:
            raise RuntimeError("The answer model has not been downloaded.")
        if self._model is None:
            import psutil
            if psutil.virtual_memory().available < 2_500_000_000:
                raise InsufficientMemoryError("At least 2.5 GB of free memory is needed to load the local answer model. Close other applications and try again; Search remains available.")
            from llama_cpp import Llama
            self._model = Llama(model_path=str(self.path), n_ctx=4096, n_threads=2,
                                n_gpu_layers=0, chat_format="chatml", verbose=False)
        self._model.reset()
        response = self._model.create_chat_completion(
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt}],
            temperature=0.0, max_tokens=300, seed=42)
        return str(response["choices"][0]["message"]["content"] or "")


class VectorStore(Protocol):
    def upsert(self, ids: list[str], texts: list[str], vectors: list[list[float]],
               project_id: str, document_id: str) -> None: ...
    def search(self, project_id: str, vector: list[float], limit: int) -> list[str]: ...
    def delete(self, project_id: str, document_id: str) -> None: ...


class ChromaVectorStore:
    def __init__(self, directory: Path):
        self.directory = directory
        self._collection = None

    def collection(self):
        if self._collection is None:
            import chromadb
            self.directory.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.directory))
            self._collection = client.get_or_create_collection("bge_small_en_v15_chunk_v1")
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

    def delete(self, project_id: str, document_id: str) -> None:
        self.collection().delete(where={"$and": [{"project_id": project_id},
                                                   {"document_id": document_id}]})
