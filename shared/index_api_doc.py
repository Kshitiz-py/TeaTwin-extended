"""Index the legacy SAP API doc into ChromaDB api-docs collection."""
import sys, os
sys.path.insert(0, '/app/git-repo')

# Configure embed provider before loading vector store
from ai_agent.llm import llm_client, ProviderConfig, provider_manager
from ai_agent.llm.ollama_provider import OllamaProvider

embed = OllamaProvider(host='http://host.docker.internal:11434', chat_model='', embed_model='qwen3-embedding:4b')
provider_manager._embed_provider = embed
provider_manager._embed_config = ProviderConfig(provider_type='ollama', host='http://host.docker.internal:11434', embed_model='qwen3-embedding:4b')

# Quick test embed
test_emb = llm_client.embed(["test"])
print(f"Embed test: {len(test_emb)} vectors, dim={len(test_emb[0]) if test_emb else 0}")

from ai_agent.rag.document_loader import DocumentChunk
from ai_agent.rag.vector_store import vector_store
from ai_agent.rag.retriever import retriever

doc_path = '/app/git-repo/shared/legacy_sap_resources.md'
print(f"Reading: {doc_path}")
print(f"Exists: {os.path.exists(doc_path)}")

with open(doc_path) as f:
    content = f.read()
print(f"File size: {len(content)} chars")

chunks = []
sections = content.split('\n## ')
for i, section in enumerate(sections):
    if section.strip():
        text = ('## ' + section) if i > 0 else section
        if len(text.strip()) > 50:
            chunks.append(DocumentChunk(
                content=text[:4000],
                metadata={
                    'collection': 'api-docs',
                    'filename': 'legacy_sap_resources.md',
                    'section': section.strip().split('\n')[0][:100],
                },
                chunk_index=i,
            ))

print(f"Indexing {len(chunks)} chunks...")
indexed = vector_store.index_documents(chunks)
print(f"Indexed {indexed} chunks")

print("Document indexed successfully into api-docs collection.")
