"""
AI Agent Service — FastAPI entry point on :8003.
Provides RAG indexing, source connection, mapping, and multi-provider LLM APIs.
On startup, optionally auto-indexes DOC_SOURCES if the ChromaDB collection is empty.
Auto-index is DISABLED by default in Docker (hangs on unreachable Ollama).
"""
import logging
import sys
import os

# Ensure project root is on path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_agent.routes import router
from ai_agent.config import AUTO_INDEX_ON_STARTUP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("ai-agent.main")

app = FastAPI(
    title="Agentic AI RAG Pipeline",
    description="AI-guided setup wizard for SAP/MES → CMSD digital twin mapping",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def startup():
    logger.info("=" * 50)
    logger.info("AI Agent Service starting on :8003")
    logger.info("LLM Provider: configurable via /api/agent/v1/agent/connect")
    logger.info("=" * 50)

    # ─── Auto-Index RAG Corpus on Startup ──────────────────
    # NOTE: Disabled by default in Docker (AUTO_INDEX_ON_STARTUP=0) because
    # embedding requires a configured LLM provider (Ollama/OpenAI).
    # In Docker, no LLM is bundled — call POST /api/agent/v1/rag/index manually
    # after configuring a provider via /api/agent/v1/agent/connect.
    if AUTO_INDEX_ON_STARTUP:
        try:
            from ai_agent.rag.vector_store import vector_store
            from ai_agent.rag.document_loader import document_loader

            doc_count = vector_store.collection.count()
            if doc_count == 0:
                logger.info("ChromaDB collection is empty — starting auto-index...")
                chunks = document_loader.load_all()
                if chunks:
                    indexed = vector_store.index_documents(chunks)
                    logger.info(f"Auto-index complete: {indexed} documents indexed")
                else:
                    logger.warning("No document chunks loaded — RAG corpus will be empty")
            else:
                logger.info(f"ChromaDB collection already has {doc_count} documents — skipping auto-index")
        except Exception as e:
            logger.warning(f"Auto-index skipped (llm embed unavailable, agent APIs still work): {e}")
    else:
        logger.info("Auto-index disabled (AUTO_INDEX_ON_STARTUP=0) — use POST /api/agent/v1/rag/index after LLM config")

@app.get("/")
async def root():
    return {"service": "AI Agent RAG Pipeline", "status": "running", "port": 8003}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
