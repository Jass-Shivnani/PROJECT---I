"""
Dione AI — Vector Store (ChromaDB)

Persistent local vector database for semantic retrieval (RAG).
Stores conversation chunks, documents, and knowledge snippets
as embeddings for fast similarity search.
"""

from typing import Optional
from loguru import logger

from server.memory.embeddings import EmbeddingService


class VectorStore:
    """
    ChromaDB-backed vector store for Dione's memory.

    Collections:
    - "conversations": Embedded conversation chunks
    - "documents": User documents, notes, files
    - "knowledge": Knowledge graph entity descriptions
    """

    def __init__(
        self,
        persist_dir: str = "data/vectorstore",
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.persist_dir = persist_dir
        self._embedding_service = embedding_service or EmbeddingService()
        self._client = None
        self._collections: dict = {}
        self._fallback_mode = False  # True = in-memory when ChromaDB fails
        self._memory_store: dict[str, list[dict]] = {}  # Fallback storage

    async def initialize(self):
        """Initialize ChromaDB and create default collections."""
        try:
            import chromadb
            from chromadb.config import Settings

            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )

            # Create default collections
            for name in ["conversations", "documents", "knowledge"]:
                self._collections[name] = self._client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"},
                )

            await self._embedding_service.initialize()
            logger.info(f"VectorStore initialized at {self.persist_dir}")

        except Exception as e:
            logger.warning(f"ChromaDB unavailable ({e}), using in-memory vector store")
            self._fallback_mode = True
            self._memory_store = {"conversations": [], "documents": [], "knowledge": []}
            await self._embedding_service.initialize()
            logger.info("VectorStore initialized (in-memory fallback)")

    async def add(
        self,
        collection: str,
        text: str,
        metadata: Optional[dict] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """Add a text to the vector store."""
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        embedding = await self._embedding_service.embed(text)

        if self._fallback_mode:
            if collection not in self._memory_store:
                self._memory_store[collection] = []
            self._memory_store[collection].append({
                "id": doc_id, "text": text,
                "embedding": embedding, "metadata": metadata or {},
            })
        else:
            if collection not in self._collections:
                self._collections[collection] = self._client.get_or_create_collection(
                    name=collection, metadata={"hnsw:space": "cosine"},
                )
            self._collections[collection].add(
                ids=[doc_id], embeddings=[embedding],
                documents=[text], metadatas=[metadata or {}],
            )

        return doc_id

    async def add_batch(
        self,
        collection: str,
        texts: list[str],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ) -> list[str]:
        """Add multiple texts at once."""
        import uuid
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        if metadatas is None:
            metadatas = [{} for _ in texts]

        embeddings = await self._embedding_service.embed_batch(texts)

        if self._fallback_mode:
            if collection not in self._memory_store:
                self._memory_store[collection] = []
            for i, text in enumerate(texts):
                self._memory_store[collection].append({
                    "id": ids[i], "text": text,
                    "embedding": embeddings[i], "metadata": metadatas[i],
                })
        else:
            if collection not in self._collections:
                self._collections[collection] = self._client.get_or_create_collection(
                    name=collection, metadata={"hnsw:space": "cosine"},
                )
            self._collections[collection].add(
                ids=ids, embeddings=embeddings,
                documents=texts, metadatas=metadatas,
            )

        return ids

    async def query(
        self,
        collection: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """Query the vector store for similar documents."""
        query_embedding = await self._embedding_service.embed(query_text)

        if self._fallback_mode:
            # In-memory cosine similarity search
            store = self._memory_store.get(collection, [])
            if not store:
                return []
            scored = []
            for doc in store:
                sim = EmbeddingService.cosine_similarity(query_embedding, doc["embedding"])
                scored.append((sim, doc))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [
                {"id": doc["id"], "text": doc["text"],
                 "metadata": doc["metadata"], "distance": 1 - sim}
                for sim, doc in scored[:n_results]
            ]

        if collection not in self._collections:
            return []

        try:
            count = self._collections[collection].count()
            if count == 0:
                return []
            results = self._collections[collection].query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, count),
                **({"where": where} if where else {}),
            )
        except Exception as e:
            logger.error(f"Vector query failed: {e}")
            return []

        documents = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                documents.append({
                    "id": doc_id,
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                })
        return documents

    async def delete(self, collection: str, doc_id: str):
        """Delete a document by ID."""
        if self._fallback_mode:
            store = self._memory_store.get(collection, [])
            self._memory_store[collection] = [d for d in store if d["id"] != doc_id]
        elif collection in self._collections:
            self._collections[collection].delete(ids=[doc_id])

    async def count(self, collection: str) -> int:
        """Get the number of documents in a collection."""
        if self._fallback_mode:
            return len(self._memory_store.get(collection, []))
        if collection in self._collections:
            return self._collections[collection].count()
        return 0

    async def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        stats = {"fallback_mode": self._fallback_mode}
        if self._fallback_mode:
            for name, store in self._memory_store.items():
                stats[name] = {"count": len(store)}
        else:
            for name, coll in self._collections.items():
                stats[name] = {"count": coll.count()}
        return stats
