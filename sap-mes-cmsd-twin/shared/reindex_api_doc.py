"""Delete old api-docs entries and re-index the updated API doc."""
import sys, os
sys.path.insert(0, '/app/git-repo')

from ai_agent.llm import llm_client, provider_manager, ProviderConfig
from ai_agent.llm.ollama_provider import OllamaProvider

embed = OllamaProvider(host='http://host.docker.internal:11434', chat_model='', embed_model='qwen3-embedding:4b')
provider_manager._embed_provider = embed
provider_manager._embed_config = ProviderConfig(provider_type='ollama', host='http://host.docker.internal:11434', embed_model='qwen3-embedding:4b')

from ai_agent.rag.vector_store import vector_store
from ai_agent.rag.document_loader import DocumentChunk

# Delete old api-docs entries
collection = vector_store.collection
try:
    existing = collection.get(include=['metadatas'])
    api_ids = [i for i, m in zip(existing['ids'], existing['metadatas']) if m and m.get('collection') == 'api-docs']
    if api_ids:
        collection.delete(ids=api_ids)
        print(f"Deleted {len(api_ids)} old api-docs entries")
except Exception as e:
    print(f"Delete warning (may be OK): {e}")

# Load and index new doc
doc_path = '/app/git-repo/shared/legacy_sap_resources.md'
with open(doc_path) as f:
    content = f.read()
print(f"Doc size: {len(content)} chars")

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

# Verify
emb_test = llm_client.embed(["test api endpoint FLD008 FLD020"])
print(f"Embed test OK: {len(emb_test[0])}d")

stats = vector_store.get_collection_stats()
print(f"Total docs after reindex: {stats}")
