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
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# ─── ChromaDB ───────────────────────────────────────────────
CHROMA_PERSIST_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "chroma_db"
)
CHROMA_COLLECTION_NAME = "cmsd-rag-corpus"
EMBEDDING_DIMENSION = 768  # nomic-embed-text v1.5

# ─── Document Sources ───────────────────────────────────────
# Paths relative to project root
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

DOC_SOURCES = [
    {
        "path": os.path.join(PROJECT_ROOT, "..", "Data_requirements_for_ASMG.md"),
        "type": "markdown",
        "collection": "data-requirements",
        "description": "Data requirements for automated simulation model generation",
    },
    {
        "path": os.path.join(PROJECT_ROOT, "cmsd_twin_service", "api_client.py"),
        "type": "code",
        "collection": "codebase",
        "description": "CMSD Twin Service API client",
    },
    {
        "path": os.path.join(PROJECT_ROOT, "cmsd_twin_service", "factory.py"),
        "type": "code",
        "collection": "codebase",
        "description": "CMSDFactory — builds CMSDDocument from API data",
    },
    {
        "path": os.path.join(PROJECT_ROOT, "mock_sap_api", "routes"),
        "type": "code_directory",
        "collection": "api-docs",
        "description": "Mock SAP API route implementations (serves as API documentation)",
    },
    {
        "path": os.path.join(PROJECT_ROOT, "mock_mes_api", "routes"),
        "type": "code_directory",
        "collection": "api-docs",
        "description": "Mock MES API route implementations (serves as API documentation)",
    },
    {
        "path": os.path.join(PROJECT_ROOT, "..", "cmsd-pydantic-master", "src", "cmsd_schema"),
        "type": "code_directory",
        "collection": "cmsd-schema",
        "description": "CMSD Pydantic schema definitions",
    },
]

# ─── Chunking ───────────────────────────────────────────────
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