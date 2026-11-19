import logging
import time
from typing import List, Dict, Any, Optional

import requests
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma
from app.ports.vector_store_port import VectorStorePort

logger = logging.getLogger("zyrabit.api")

# Transient transport failures are retried; HTTP/logical errors fail immediately.
_RETRY_DELAYS = (1.0, 2.0, 4.0)


class DirectOllamaEmbeddings(Embeddings):
    """
    Direct Ollama API Embeddings (LangChain Compatible).
    Bypasses library bugs by using raw HTTP requests. Handles fallback for embedded runtimes.
    """
    def __init__(
        self,
        model: str,
        base_url: str,
        timeout_seconds: float = 60.0,
        batch_size: int = 5,
        max_retries: int = 3,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = max(float(timeout_seconds), 1.0)
        self.batch_size = max(int(batch_size), 1)
        self.max_retries = max(int(max_retries), 1)
        self._last_failure_detail: Optional[str] = None
        self._last_latency_seconds: Optional[float] = None
        self._recovered_after_timeout: bool = False

    def _record_failure(self, detail: str) -> None:
        self._last_failure_detail = detail
        logger.error("Embedding failure at %s: %s", self.base_url, detail)

    def _record_success(self, latency_seconds: float, recovered_after_timeout: bool) -> None:
        self._last_latency_seconds = latency_seconds
        self._last_failure_detail = None
        self._recovered_after_timeout = recovered_after_timeout

    def _embed_batch(self, batch: List[str]) -> List[List[float]]:
        last_exc: Exception | None = None
        saw_timeout = False
        attempts = min(self.max_retries, len(_RETRY_DELAYS))

        for attempt in range(attempts):
            started = time.perf_counter()
            try:
                response = requests.post(
                    f"{self.base_url}/api/embed",
                    json={
                        "model": self.model,
                        "input": batch,
                    },
                    timeout=self.timeout_seconds,
                )
                if response.status_code != 200:
                    logger.error("⚠️ Ollama Error (%s): %s", response.status_code, response.text)
                response.raise_for_status()
                embeddings = response.json()["embeddings"]
                latency = time.perf_counter() - started
                self._record_success(latency, recovered_after_timeout=saw_timeout)
                return embeddings
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                saw_timeout = isinstance(exc, requests.exceptions.Timeout) or saw_timeout
                last_exc = exc
                detail = f"{type(exc).__name__}: {exc}"
                if attempt < attempts - 1:
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning(
                        "Embedding retry %s/%s after %s (waiting %.1fs)",
                        attempt + 1,
                        attempts,
                        detail,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                self._record_failure(detail)
            except Exception as exc:
                self._record_failure(f"{type(exc).__name__}: {exc}")
                raise RuntimeError(
                    f"Embedding provider unavailable at {self.base_url}; document was not indexed. "
                    "Configure EMBEDDING_URL independently from SLM_URL."
                ) from exc

        raise RuntimeError(
            f"Embedding provider unavailable at {self.base_url}; document was not indexed. "
            "Configure EMBEDDING_URL independently from SLM_URL."
        ) from last_exc

    def _embed(self, texts: List[str]) -> List[List[float]]:
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            all_embeddings.extend(self._embed_batch(batch))
        return all_embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]

    def health(self) -> tuple[bool, str]:
        """Report readiness including recent embed failures and latency degradation."""
        if self._last_failure_detail:
            return False, f"recent embedding failure: {self._last_failure_detail}"

        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2.0)
            response.raise_for_status()
            models = response.json().get("models", [])
            names = {item.get("name") for item in models if isinstance(item, dict)}
            # Ollama exposes the default tag as `model:latest`, while its API
            # accepts both that name and the convenient tagless alias.
            configured_names = {self.model, f"{self.model}:latest"}
            if names and not configured_names.intersection(names):
                return False, f"embedding model '{self.model}' is not installed"

            detail = f"{self.model} available"
            if self._last_latency_seconds is not None:
                detail = f"{detail}; last embed {self._last_latency_seconds:.1f}s"
            # A success that only arrived after a timeout retry is still degraded:
            # CPU hosts that need retries will show DEGRADED until a clean call.
            if self._recovered_after_timeout:
                return False, f"{detail}; recovered after timeout retry"
            # Soft latency degradation: last successful call used most of the budget.
            if (
                self._last_latency_seconds is not None
                and self._last_latency_seconds >= self.timeout_seconds * 0.8
            ):
                return False, f"{detail}; latency near timeout budget ({self.timeout_seconds:.0f}s)"
            return True, detail
        except Exception as exc:
            return False, f"embedding endpoint unavailable at {self.base_url}: {exc}"


class ChromaAdapter(VectorStorePort):
    """
    Bridge between our VectorStorePort and LangChain's Chroma.
    """
    def __init__(self, langchain_chroma: Chroma):
        self.vector_store = langchain_chroma

    def similarity_search(self, query_text: str, k: int = 5) -> List[Any]:
        return self.vector_store.similarity_search(query_text, k=k)

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        self.vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    def add_documents(self, documents: List[Any]) -> None:
        self.vector_store.add_documents(documents)

    def delete(self, where: Dict[str, Any]) -> None:
        # Simplified delete for Chroma V0.5+
        pass

    def heartbeat(self) -> bool:
        """
        Real connectivity check for ChromaDB.
        """
        try:
            # We try to access the underlying chroma client heartbeat
            if hasattr(self.vector_store, "_client"):
                self.vector_store._client.heartbeat()
                return True
            return False
        except Exception as e:
            logger.error(f"❌ ChromaDB Heartbeat failed: {e}")
            return False
