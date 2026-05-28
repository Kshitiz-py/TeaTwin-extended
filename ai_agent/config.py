"""
AI Agent configuration — Ollama API, ChromaDB, embedding, and RAG settings.
"""

import os

# ─── Ollama Cloud API ───────────────────────────────────────
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
# Model for chat/reasoning
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen3.5:397b-cloud")
# Model for embeddings (runs locally or via Ollama)
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "qwen3-embedding:4b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# ─── ChromaDB ───────────────────────────────────────────────
# In Docker: /app/sap-mes-cmsd-twin/ai_agent/../chroma_db → /app/sap-mes-cmsd-twin/chroma_db
# Volume mount overrides this at runtime
CHROMA_PERSIST_DIR = os.getenv(
    "CHROMA_PERSIST_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "chroma_db")
)
CHROMA_COLLECTION_NAME = "cmsd-rag-corpus"
EMBEDDING_DIMENSION = 2560  # qwen3-embedding:4b

# ─── Auto-Indexing ──────────────────────────────────────────
# When True, the ai-agent automatically indexes all DOC_SOURCES on startup
# if the ChromaDB collection is empty. Set to "0" to disable.
AUTO_INDEX_ON_STARTUP = os.getenv("AUTO_INDEX_ON_STARTUP", "1") == "1"

# ─── Document Sources ───────────────────────────────────────
# NOTE: The mock SAP/MES Python code is intentionally EXCLUDED from RAG.
# In production, only API documentation, CMSD schema, data requirements,
# and our own service code are available. The mapping agent works from
# API docs + CMSD schema + data requirements — not from source code of
# external systems.
# Paths relative to project root
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

DOC_SOURCES = [
    # ── Markdown / Requirements ────────────────────────────
    {
        "path": os.path.join(PROJECT_ROOT, "..", "Data_requirements_for_ASMG.md"),
        "type": "markdown",
        "collection": "data-requirements",
        "description": "Data requirements for automated simulation model generation (ASMG) — defines minimum data needed for CMSD twin",
    },
    # ── CMSD Pydantic Schema (target: what we map TO) ───────
    {
        "path": os.path.join(PROJECT_ROOT, "..", "cmsd-pydantic-master", "src", "cmsd_schema"),
        "type": "code_directory",
        "collection": "cmsd-schema",
        "description": "CMSD v2 Pydantic schema — all entity models the agent maps SAP/MES data INTO (Resource, PartType, BOM, ProcessPlan, Order, Job, Calendar, Layout, Connection, InventoryItem, MaintenancePlan, etc.)",
    },
    # ── CMSD Twin Service (our runtime: how we build the twin)
    {
        "path": os.path.join(PROJECT_ROOT, "cmsd_twin_service"),
        "type": "code_directory",
        "collection": "codebase",
        "description": "CMSD Twin Service — transforms SAP+MES API data into a live CMSDDocument digital twin (orchestrator, factory, change detector, event bus, API client)",
    },
    # ── AI Agent Internals (self-documenting for agent reasoning)
    {
        "path": os.path.join(PROJECT_ROOT, "ai_agent"),
        "type": "code_directory",
        "collection": "codebase",
        "description": "AI Agent service — RAG pipeline, mapping engine, API explorer, connection manager, code generation orchestrator, and agentic reviewer/writer/tester pipeline",
    },
    # ── Shared Configuration ────────────────────────────────
    {
        "path": os.path.join(PROJECT_ROOT, "shared", "config.py"),
        "type": "code",
        "collection": "codebase",
        "description": "Shared AppConfig — DatabaseConfig, ServiceConfig, OrchestratorConfig aggregation used by all services",
    },
]

# ─── Chunking ──────────────────────────────────────────────
CHUNK_SIZE = 1024
CHUNK_OVERLAP = 128

# ─── API Documentation ──────────────────────────────────────
# User-uploaded API docs go here
API_DOCS_DIR = os.path.join(PROJECT_ROOT, "ai_agent", "api_docs")

# ─── Agent Reports ──────────────────────────────────────────
REPORTS_DIR = os.path.join(PROJECT_ROOT, ".agent-reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# ─── Retry Settings ─────────────────────────────────────────
MAX_GENERATION_RETRIES = 3
MAX_REVIEWER_RETRIES = 2
