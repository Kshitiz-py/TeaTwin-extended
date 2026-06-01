"""Debug: check if api-docs docs show up in RAG queries."""
import sys, os
sys.path.insert(0, '/app/git-repo')

from ai_agent.llm import llm_client, provider_manager, ProviderConfig
from ai_agent.llm.ollama_provider import OllamaProvider

# Configure embed
embed = OllamaProvider(host='http://host.docker.internal:11434', chat_model='', embed_model='qwen3-embedding:4b')
provider_manager._embed_provider = embed
provider_manager._embed_config = ProviderConfig(provider_type='ollama', host='http://host.docker.internal:11434', embed_model='qwen3-embedding:4b')

from ai_agent.rag.vector_store import vector_store
from ai_agent.rag.retriever import retriever

# Check stats
stats = vector_store.get_collection_stats()
print(f"Total docs in ChromaDB: {stats}")

# Test the retriever directly
print("\n=== Retriever query ===")
results = retriever.retrieve(
    "API endpoint implementation /legacy/r route handler",
    top_k=3,
    collections=["api-docs"],
)
print(f"api-docs results: {len(results)}")
for r in results:
    fname = r.get("metadata", {}).get("filename", "?")
    print(f"  - {fname}: {r['content'][:150]}...")

# Try broader query
print("\n=== Broader retriever query ===")
results2 = retriever.retrieve(
    "legacy SAP FLD008 FLD020 field mapping resource factory machine endpoint documentation",
    top_k=3,
    collections=["api-docs"],
)
print(f"api-docs results: {len(results2)}")
for r in results2:
    fname = r.get("metadata", {}).get("filename", "?")
    print(f"  - {fname}: {r['content'][:150]}...")
