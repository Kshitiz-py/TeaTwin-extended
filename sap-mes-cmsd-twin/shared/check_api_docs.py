"""Check api-docs collection content."""
import sys, os
sys.path.insert(0, '/app/git-repo')

from ai_agent.llm import llm_client, provider_manager, ProviderConfig
from ai_agent.llm.ollama_provider import OllamaProvider

embed = OllamaProvider(host='http://host.docker.internal:11434', chat_model='', embed_model='qwen3-embedding:4b')
provider_manager._embed_provider = embed
provider_manager._embed_config = ProviderConfig(provider_type='ollama', host='http://host.docker.internal:11434', embed_model='qwen3-embedding:4b')

from ai_agent.rag.vector_store import vector_store

# Get ALL documents in api-docs collection
stats = vector_store.get_collection_stats()
print(f"Total docs: {stats}")

# Query for api-docs using a very generic query
results = vector_store.query("api endpoint documentation legacy field mapping", n_results=50)
api_docs_found = [r for r in results if r.get('metadata', {}).get('collection') == 'api-docs']
print(f"api-docs found in top 50: {len(api_docs_found)}")
for r in api_docs_found:
    print(f"  ID: {r.get('id', '?')}")
    print(f"  File: {r.get('metadata', {}).get('filename', '?')}")
    print(f"  Content[:100]: {r['content'][:100]}")
    print()

# Check if we have duplicates (same ID multiple times)
from chromadb import PersistentClient
import os
chroma_dir = '/app/chromadb_data'
client = PersistentClient(path=chroma_dir)
collection = client.get_collection('cmsd-rag-corpus')
# Get all docs with api-docs metadata
all_data = collection.get(include=['metadatas', 'documents'])
api_ids = [i for i, m in zip(all_data['ids'], all_data['metadatas']) if m and m.get('collection') == 'api-docs']
print(f"Total api-docs in collection: {len(api_ids)}")
print(f"API doc IDs: {api_ids}")
