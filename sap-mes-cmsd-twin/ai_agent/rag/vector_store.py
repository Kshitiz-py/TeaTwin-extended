"""
Vector Store — ChromaDB wrapper for storing and querying document embeddings.
Supports persistent storage and collection management.
"""

import os
import logging

import chromadb
from chromadb.config import Settings as ChromaSettings

from ..config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, EMBEDDING_DIMENSION
from ..llm import llm_client

logger = logging.getLogger("ai-agent.vector-store")


class VectorStore:
    """ChromaDB vector store for document embeddings."""

    def __init__(self, persist_dir: str | None = None):
        self.persist_dir = persist_dir or CHROMA_PERSIST_DIR
        os.makedirs(self.persist_dir, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(
                name=CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def index_documents(self, chunks: list) -> int:
        """
        Embed and index a list of DocumentChunk objects.
        Returns the number of documents indexed.
        """
        if not chunks:
            return 0

        # Generate embeddings via Ollama
        texts = [chunk.content for chunk in chunks]
        logger.info(f"Generating embeddings for {len(texts)} chunks...")

        embeddings = []
        for i, text in enumerate(texts):
            # Truncate very long texts to avoid embedding failures
            truncated = text[:4000] if len(text) > 4000 else text
            try:
                emb = llm_client.embed([truncated])
                if emb:
                    embeddings.append(emb[0])
                else:
                    embeddings.append([0.0] * EMBEDDING_DIMENSION)
            except Exception as e:
                logger.warning(f"Embedding failed for chunk {i}: {e}")
                embeddings.append([0.0] * EMBEDDING_DIMENSION)

        # Prepare ChromaDB documents
        ids = []
        documents = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{chunk.metadata.get('collection', 'unknown')}_{chunk.metadata.get('filename', '')}_{i}"
            ids.append(chunk_id)
            documents.append(chunk.content[:8000])  # ChromaDB text limit
            metadatas.append(chunk.metadata)

        # Add to collection
        try:
            # Check if documents already exist and upsert
            existing = self.collection.get(ids=ids[:min(10, len(ids))])
            if existing and existing.get("ids") and len(existing["ids"]) > 0:
                logger.info("Upserting existing documents...")
                self.collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                )
            else:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                )
        except Exception as e:
            logger.error(f"Failed to add documents to ChromaDB: {e}")
            # Fallback: add one by one
            for i in range(len(ids)):
                try:
                    self.collection.upsert(
                        ids=[ids[i]],
                        embeddings=[embeddings[i]],
                        documents=[documents[i]],
                        metadatas=[metadatas[i]],
                    )
                except Exception as inner_e:
                    logger.error(f"Failed to add chunk {ids[i]}: {inner_e}")

        logger.info(f"Indexed {len(ids)} documents in ChromaDB")
        return len(ids)

    def query(
        self,
        query_text: str,
        n_results: int = 5,
    ) -> list[dict]:
        """
        Query the vector store for semantically similar documents.
        Returns a list of {content, metadata, score} dicts.
        """
        # Generate query embedding
        try:
            query_emb = llm_client.embed([query_text[:4000]])
            if not query_emb:
                return []
            query_embedding = query_emb[0]
        except Exception as e:
            logger.error(f"Query embedding failed: {e}")
            return []

        # Query ChromaDB (without where filter — filter in Python to avoid
        # ChromaDB metadata indexing issues)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=max(n_results * 10, 40),
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        formatted = []
        if results and results.get("ids") and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                doc = results["documents"][0][i] if results.get("documents") else ""
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                if meta is None:
                    meta = {}
                distance = results["distances"][0][i] if results.get("distances") else 1.0
                # Convert cosine distance to similarity score (0-1)
                score = max(0.0, 1.0 - float(distance))

                formatted.append({
                    "content": doc,
                    "metadata": meta,
                    "score": round(score, 4),
                })

        return formatted

    def get_collection_stats(self) -> dict:
        """Return statistics about the indexed collection."""
        return {
            "name": CHROMA_COLLECTION_NAME,
            "document_count": self.collection.count(),
            "persist_dir": self.persist_dir,
        }

    def clear(self):
        """Delete all documents from the collection."""
        try:
            self._client.delete_collection(CHROMA_COLLECTION_NAME)
            self._collection = None
            logger.info("Collection cleared")
        except Exception as e:
            logger.warning(f"Failed to clear collection: {e}")


# Singleton
vector_store = VectorStore()
