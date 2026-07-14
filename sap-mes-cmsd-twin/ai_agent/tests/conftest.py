"""
Test fixtures for ai_agent route tests.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def client():
    """FastAPI TestClient with mocked dependencies."""
    # Pre-seed modules with import-time side effects
    _mock_mods = {
        "chromadb": MagicMock(),
        "chromadb.config": MagicMock(),
        "ollama": MagicMock(),
        "ai_agent.rag.vector_store": MagicMock(),
        "ai_agent.rag.document_loader": MagicMock(),
        "ai_agent.rag.retriever": MagicMock(),
        "ai_agent.mapping_engine": MagicMock(),
        "ai_agent.llm.provider_manager": MagicMock(),
        "ai_agent.llm": MagicMock(),
        "ai_agent.code_generation": MagicMock(),
        "ai_agent.code_generation.orchestrator": MagicMock(),
        "ai_agent.code_generation.git_manager": MagicMock(),
    }

    _saved = {}
    for name, mod in _mock_mods.items():
        if name in sys.modules:
            _saved[name] = sys.modules[name]
        sys.modules[name] = mod

    try:
        import ai_agent.routes as routes_mod
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        mock_explorer = AsyncMock()
        mock_explorer.fetch_payload = AsyncMock()
        mock_explorer.analyze_payload = MagicMock()
        mock_explorer.extract_field_paths = MagicMock()
        mock_conn_mgr = MagicMock()

        app = FastAPI()
        app.include_router(routes_mod.router)

        with patch.object(routes_mod, "api_explorer", mock_explorer), \
             patch.object(routes_mod, "connection_manager", mock_conn_mgr):
            with TestClient(app) as tc:
                tc.app.state.mock_explorer = mock_explorer
                tc.app.state.mock_conn_mgr = mock_conn_mgr
                yield tc

    finally:
        for name in _mock_mods:
            if name in _saved:
                sys.modules[name] = _saved[name]
            elif name in sys.modules:
                del sys.modules[name]
