"""
Index Corpus — Standalone script to embed and index all configured document sources.
Run: python -m ai_agent.index_corpus
"""

import logging
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_agent.rag.document_loader import document_loader
from ai_agent.rag.vector_store import vector_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("index-corpus")


def main():
    logger.info("=" * 60)
    logger.info("Phase A: Indexing RAG Corpus")
    logger.info("=" * 60)

    # Step 1: Load all documents
    logger.info("Step 1/3: Loading document sources...")
    chunks = document_loader.load_all()
    logger.info(f"  Loaded {len(chunks)} chunks from all sources")

    if not chunks:
        logger.error("No chunks loaded — check DOC_SOURCES paths in config.py")
        return 1

    # Step 2: Index into ChromaDB (embeddings generated via Ollama)
    logger.info("Step 2/3: Indexing chunks into ChromaDB (this may take a while)...")
    indexed = vector_store.index_documents(chunks)
    logger.info(f"  Indexed {indexed} documents")

    # Step 3: Print stats
    logger.info("Step 3/3: Verifying...")
    stats = vector_store.get_collection_stats()
    logger.info(f"  Collection: {stats['name']}")
    logger.info(f"  Documents:  {stats['document_count']}")
    logger.info(f"  Storage:    {stats['persist_dir']}")

    logger.info("=" * 60)
    logger.info("Phase A indexing complete!")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
