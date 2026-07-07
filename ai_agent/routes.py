"""
AI Agent REST API — /api/agent/v1/* endpoints.
Provides source management, RAG indexing, mapping analysis, and LLM provider config.
Code generation (Writer→Reviewer→Tester→Git) is now a host-side CLI tool.
Enhanced with multi-endpoint support, raw payload display, and smart reanalysis.
"""
import asyncio
import json
import logging
import os
import traceback
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .connection_manager import connection_manager
from .rag.vector_store import vector_store
from .rag.document_loader import document_loader
from .mapping_engine import mapping_engine, TRANSFORMATION_PRESETS
from .api_explorer import api_explorer
from .llm import llm_client, PROVIDER_PRESETS
from .odata_ingest import odata_ingestor
from .recommender import endpoint_recommender

logger = logging.getLogger("ai-agent.routes")

router = APIRouter(prefix="/api/agent/v1")

# ─── Request Models ────────────────────────────────────────

class SourceConfig(BaseModel):
    name: str
    base_url: str
    auth_type: str = "none"
    username: str = ""
    password: str = ""
    token: str = ""
    api_key: str = ""
    api_key_header: str = "X-API-Key"
    extra_headers: dict[str, str] = {}

class EndpointSpec(BaseModel):
    """Specification for a single API endpoint to analyze."""
    source_id: str
    endpoint: str
    method: str = "GET"
    label: str = ""  # optional label e.g. "SAP Resources"

class ApprovedPayload(BaseModel):
    """Pre-fetched payload sent by the frontend for analysis."""
    endpoint: str
    source_id: str
    label: str = ""
    raw_payload: Any = None

class MappingAnalyzeRequest(BaseModel):
    source_id: str = ""
    data_point_name: str
    cmsd_entity: str
    api_endpoint: str = ""
    endpoints: list[EndpointSpec] = []
    method: str = "GET"
    approved_payloads: list[ApprovedPayload] = []

class MappingChatRequest(BaseModel):
    data_point_name: str
    current_mapping: dict[str, Any]
    user_question: str

class MappingEditsRequest(BaseModel):
    current_mapping: dict[str, Any]
    edits: dict[str, Any]

class SmartReanalyzeRequest(BaseModel):
    data_point_name: str
    cmsd_entity: str
    current_mapping: dict[str, Any]
    user_guidance: str
    endpoints: list[EndpointSpec] = []

class FetchEndpointsRequest(BaseModel):
    """Request model for POST /mapping/fetch — fire one or more endpoints."""
    endpoints: list[EndpointSpec]


class DiscoverRequest(BaseModel):
    """Request model for POST /sources/{id}/discover — ingest SAP OData $metadata."""
    entity_set_filter: list[str] | None = None


class SampleRequest(BaseModel):
    """Request model for POST /sources/{id}/sample — local-only row preview."""
    entity_set: str
    top: int = 3


class RecommendRequest(BaseModel):
    """Request model for POST /mapping/recommend-endpoints."""
    source_id: str
    cmsd_entity: str


# ─── Provider Models ───────────────────────────────────────

class ProviderConfigModel(BaseModel):
    """Configuration for a single LLM provider (chat or embedding)."""
    provider_type: str = "ollama"  # ollama, openai, anthropic, deepseek, together, grok
    host: str = ""
    api_key: str = ""
    chat_model: str = ""
    embed_model: str = ""


class MultiProviderConfig(BaseModel):
    """Configuration for chat + optional separate embedding provider."""
    chat: ProviderConfigModel
    embed: ProviderConfigModel | None = None


class ProviderListResponse(BaseModel):
    """Single provider entry in the marketplace list."""
    name: str
    label: str
    api_style: str
    host: str
    chat_model: str
    embed_model: str
    has_embeddings: bool
    requires_api_key: bool
    description: str


# ─── Health ─────────────────────────────────────────────────

@router.get("/health")
async def health():
    return {"status": "ok", "service": "ai-agent"}


# ─── LLM Provider Connection ───────────────────────────────

@router.get("/agent/providers")
async def list_providers():
    """Return all available market LLM provider presets with their defaults.

    The frontend uses this to populate the provider dropdown.
    Provider secrets (API keys) are **never** included.
    """
    _LABELS: dict[str, str] = {
        "ollama": "Ollama (Local)",
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "deepseek": "DeepSeek",
        "together": "Together AI",
        "grok": "xAI Grok",
        "openrouter": "OpenRouter",
        "perplexity": "Perplexity",
        "github-models": "GitHub Models",
        "custom": "Custom (OpenAI-compatible)",
    }
    _DESC: dict[str, str] = {
        "ollama": "Self-hosted, fully private. Supports embeddings.",
        "openai": "GPT-4o, o3, o4-mini. Embeddings via text-embedding-3.",
        "anthropic": "Claude Sonnet 4, Opus. No native embeddings.",
        "deepseek": "DeepSeek-V3, R1. Cost-effective reasoning.",
        "together": "Multi-model marketplace. Mixtral, Llama, etc.",
        "grok": "xAI Grok-2, Grok-3. OpenAI-compatible API.",
        "openrouter": "Unified API for 200+ models. Pay-per-token.",
        "perplexity": "Sonar, Sonar Pro. Search-augmented models.",
        "github-models": "GitHub Marketplace models. Azure-hosted.",
        "custom": "Any OpenAI-compatible endpoint (vLLM, LiteLLM, etc.).",
    }
    _REQUIRES_KEY: set[str] = {"openai", "anthropic", "deepseek", "together", "grok",
                                 "openrouter", "perplexity", "github-models"}

    providers = []
    for name, preset in PROVIDER_PRESETS.items():
        providers.append(ProviderListResponse(
            name=name,
            label=_LABELS.get(name, name.title()),
            api_style=preset.get("api_style", "openai"),
            host=preset.get("host", ""),
            chat_model=preset.get("chat_model", ""),
            embed_model=preset.get("embed_model", ""),
            has_embeddings=bool(preset.get("embed_model", "")),
            requires_api_key=(name in _REQUIRES_KEY),
            description=_DESC.get(name, ""),
        ).model_dump())

    return {"providers": providers}


@router.get("/agent/status")
async def agent_status():
    """Return the current LLM provider connection state."""
    return llm_client.get_config()


@router.post("/agent/connect")
async def connect_agent(config: MultiProviderConfig):
    """Configure the LLM provider and test the connection.

    Accepts provider configuration. API keys are stored **in memory only**
    — never persisted to disk.
    Supports separate embedding provider via config.embed.
    """
    llm_client.configure(
        api_style=config.chat.provider_type,
        host=config.chat.host,
        api_key=config.chat.api_key or "",
        chat_model=config.chat.chat_model,
        embed_model=config.chat.embed_model,
    )

    # Configure separate embedding provider if provided
    if config.embed and config.embed.host:
        logger.info(f"Configuring embed provider: type={config.embed.provider_type}, host={config.embed.host}, model={config.embed.embed_model}")
        llm_client.configure_embed(
            api_style=config.embed.provider_type,
            host=config.embed.host,
            api_key=config.embed.api_key or "",
            embed_model=config.embed.embed_model,
        )
    elif config.embed:
        logger.warning(f"Embed config provided but host is empty — skipping")

    test_result = llm_client.test_connection()

    # Also test embed provider if separate
    if config.embed:
        embed_test = llm_client.test_embed_connection()
        test_result["embed"] = embed_test

    return {
        "configured": True,
        "provider": config.chat.provider_type,
        "host": config.chat.host,
        "chat_model": config.chat.chat_model,
        "embed_model": (config.embed.embed_model if config.embed else config.chat.embed_model),
        "connection_test": test_result,
    }


@router.post("/agent/test")
async def test_agent_connection():
    """Test connectivity to the currently configured provider."""
    return llm_client.test_connection()


@router.post("/agent/disconnect")
async def disconnect_agent():
    """Close all LLM provider connections (API keys flushed from memory)."""
    return llm_client.disconnect()


@router.get("/agent/models")
async def list_agent_models():
    """List available models from the currently configured chat provider.
    
    Requires an active provider connection. Returns model IDs and names.
    """
    try:
        models = llm_client.list_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(500, f"Failed to list models: {e}")


# ─── Sources ────────────────────────────────────────────────

@router.post("/sources")
async def add_source(source: SourceConfig):
    """Add or update a data source configuration."""
    config = source.model_dump()
    result = connection_manager.add_source(config)
    return result

@router.get("/sources")
async def list_sources():
    """List all configured data sources."""
    return {"sources": connection_manager.list_sources()}

@router.get("/sources/{source_id}")
async def get_source(source_id: str):
    """Get a source by ID."""
    source = connection_manager.get_source(source_id)
    if not source:
        raise HTTPException(404, f"Source '{source_id}' not found")
    return source

@router.post("/sources/{source_id}/test")
async def test_source(source_id: str):
    """Test connectivity to a data source."""
    result = await connection_manager.test_connection(source_id)
    return result

@router.delete("/sources/{source_id}")
async def remove_source(source_id: str):
    """Remove a data source."""
    removed = connection_manager.remove_source(source_id)
    if not removed:
        raise HTTPException(404, f"Source '{source_id}' not found")
    return {"removed": True, "source_id": source_id}


# ─── SAP OData Discovery (deterministic; the LLM never connects to SAP) ────

@router.post("/sources/{source_id}/discover")
async def discover_source(source_id: str, request: DiscoverRequest):
    """Fetch SAP OData $metadata, parse it into a metadata-only SourceSchema,
    persist the schema, and index metadata-only chunks into the `source-schema`
    RAG corpus. Deterministic — no LLM, no row data."""
    try:
        return await odata_ingestor.discover(source_id, request.entity_set_filter)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Discover failed for {source_id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(502, f"Discover failed: {e}")


@router.get("/sources/{source_id}/schema")
async def get_source_schema(source_id: str, entity_set: str | None = None):
    """Return the persisted SourceSchema (metadata only) for UI browsing."""
    schema = odata_ingestor.load_schema(source_id, entity_set=entity_set)
    if schema is None:
        raise HTTPException(404, f"No schema for source '{source_id}'. Run /discover first.")
    return {"source_schema": schema.to_dict()}


@router.post("/sources/{source_id}/sample")
async def sample_source(source_id: str, request: SampleRequest):
    """Fetch a few rows from a SAP OData entity set for LOCAL UI preview only.

    Row data is returned to the browser; it is NEVER sent to the LLM and NEVER
    indexed in RAG. This is the only source endpoint that returns row data.
    """
    try:
        return await odata_ingestor.sample(source_id, request.entity_set, request.top)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Sample failed for {source_id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(502, f"Sample failed: {e}")


# ─── RAG Indexing ──────────────────────────────────────────

@router.post("/rag/index")
async def index_corpus():
    """Index all configured document sources into ChromaDB."""
    try:
        chunks = document_loader.load_all()
        indexed = vector_store.index_documents(chunks)
        stats = vector_store.get_collection_stats()
        return {
            "success": True,
            "chunks_loaded": len(chunks),
            "documents_indexed": indexed,
            "collection_stats": stats,
        }
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise HTTPException(500, f"Indexing failed: {e}")

@router.get("/rag/stats")
async def get_rag_stats():
    """Get ChromaDB collection statistics."""
    return vector_store.get_collection_stats()


# ─── Mapping ────────────────────────────────────────────────

@router.post("/mapping/recommend-endpoints")
async def recommend_endpoints(request: RecommendRequest):
    """Recommend a covering set of SAP OData endpoints for a CMSD entity.

    LLM-over-RAG (metadata only). The LLM never connects to SAP and never sees row
    data. Requires the source to have been discovered first (POST /sources/{id}/discover)
    so its source-schema is indexed in the RAG corpus.
    """
    try:
        return await endpoint_recommender.recommend(request.source_id, request.cmsd_entity)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Recommend failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(502, f"Recommend failed: {e}")


@router.post("/mapping/analyze")
async def analyze_mapping(request: MappingAnalyzeRequest):
    """
    Propose field mapping for a given data point and CMSD entity.
    Supports two modes:
    1. Pre-fetched: frontend sends approved_payloads[] with raw_payload already fetched.
    2. Live-fetch (legacy): backend fetches payloads from specified endpoints/source.
    Uses RAG retrieval + LLM reasoning.
    """
    try:
        payload_analyses: list[dict] = []
        all_endpoints_str: list[str] = []

        if request.approved_payloads:
            # ── Mode 1: Pre-fetched payloads from Phase 1 approval ──
            for ap in request.approved_payloads:
                if ap.raw_payload is None:
                    continue
                payload_analysis = api_explorer.analyze_payload(ap.raw_payload)
                payload_analyses.append({
                    "endpoint": ap.endpoint,
                    "source_label": ap.label or ap.endpoint,
                    "analysis": payload_analysis,
                    "raw_payload": ap.raw_payload,
                })
                all_endpoints_str.append(f"{ap.source_id}{ap.endpoint}")
        else:
            # ── Mode 2: Live-fetch from endpoints ──
            endpoints_to_fetch: list[dict] = []
            if request.endpoints:
                for ep in request.endpoints:
                    endpoints_to_fetch.append({
                        "source_id": ep.source_id,
                        "endpoint": ep.endpoint,
                        "method": ep.method,
                        "label": ep.label or ep.endpoint,
                    })
            elif request.source_id and request.api_endpoint:
                endpoints_to_fetch.append({
                    "source_id": request.source_id,
                    "endpoint": request.api_endpoint,
                    "method": request.method,
                    "label": request.api_endpoint,
                })

            if not endpoints_to_fetch:
                raise HTTPException(400, "No endpoints or approved_payloads specified")

            for ep in endpoints_to_fetch:
                payload_result = await api_explorer.fetch_payload(
                    source_id=ep["source_id"],
                    endpoint=ep["endpoint"],
                    method=ep.get("method", "GET"),
                )
                payload_analysis = api_explorer.analyze_payload(payload_result["payload"])
                payload_analyses.append({
                    "endpoint": ep["endpoint"],
                    "source_label": ep.get("label", ep["endpoint"]),
                    "analysis": payload_analysis,
                    "raw_payload": payload_result["payload"],
                })
                all_endpoints_str.append(ep["endpoint"])

        if not payload_analyses:
            raise HTTPException(400, "No valid payloads to analyze")

        # Get RAG context
        rag_context = await mapping_engine.analyze_rag(
            data_point_name=request.data_point_name,
            cmsd_entity=request.cmsd_entity,
            api_endpoint=", ".join(all_endpoints_str),
        )

        # Propose mapping (single or multi)
        if len(payload_analyses) == 1:
            mapping = await mapping_engine.propose_mapping(
                data_point_name=request.data_point_name,
                cmsd_entity=request.cmsd_entity,
                api_endpoint=all_endpoints_str[0],
                payload_analysis=payload_analyses[0]["analysis"],
                rag_context=rag_context,
            )
        else:
            endpoint_labels = [pa["source_label"] for pa in payload_analyses]
            mapping = await mapping_engine.propose_mapping_multi(
                data_point_name=request.data_point_name,
                cmsd_entity=request.cmsd_entity,
                endpoint_labels=endpoint_labels,
                payload_analyses=payload_analyses,
                rag_context=rag_context,
            )

        return {
            "success": True,
            "cmsd_entity": request.cmsd_entity,
            "mapping": mapping,
            "proposed_mapping": mapping,  # backward compat for GuidedMapping
            "rag_context": rag_context,
        }
    except Exception as e:
        logger.error(f"Mapping analysis failed: {e}")
        raise HTTPException(500, f"Mapping analysis failed: {e}")


def _sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post("/mapping/analyze-stream")
async def analyze_mapping_stream(request: MappingAnalyzeRequest):
    """
    Propose field mapping with real-time progress via Server-Sent Events.
    Returns SSE stream with events: step (progress) and result (final mapping).
    """
    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            # Phase 1: Parse payloads
            yield _sse_event("step", {"phase": "payloads", "status": "running", "label": "Parsing API payloads..."})
            await asyncio.sleep(0.05)  # flush SSE so frontend renders the phase

            payload_analyses: list[dict] = []
            all_endpoints_str: list[str] = []

            if request.approved_payloads:
                for ap in request.approved_payloads:
                    if ap.raw_payload is None:
                        continue
                    analysis = api_explorer.analyze_payload(ap.raw_payload)
                    payload_analyses.append({
                        "endpoint": ap.endpoint,
                        "source_label": ap.label or ap.endpoint,
                        "analysis": analysis,
                        "raw_payload": ap.raw_payload,
                    })
                    all_endpoints_str.append(f"{ap.source_id}{ap.endpoint}")
            else:
                endpoints_to_fetch = []
                if request.endpoints:
                    for ep in request.endpoints:
                        endpoints_to_fetch.append({
                            "source_id": ep.source_id, "endpoint": ep.endpoint,
                            "method": ep.method, "label": ep.label or ep.endpoint,
                        })
                elif request.source_id and request.api_endpoint:
                    endpoints_to_fetch.append({
                        "source_id": request.source_id, "endpoint": request.api_endpoint,
                        "method": request.method, "label": request.api_endpoint,
                    })

                if not endpoints_to_fetch:
                    yield _sse_event("error", {"message": "No endpoints or approved_payloads specified"})
                    return

                for ep in endpoints_to_fetch:
                    result = await api_explorer.fetch_payload(ep["source_id"], ep["endpoint"], ep.get("method", "GET"))
                    analysis = api_explorer.analyze_payload(result["payload"])
                    payload_analyses.append({
                        "endpoint": ep["endpoint"], "source_label": ep.get("label", ep["endpoint"]),
                        "analysis": analysis, "raw_payload": result["payload"],
                    })
                    all_endpoints_str.append(ep["endpoint"])

            if not payload_analyses:
                yield _sse_event("error", {"message": "No valid payloads to analyze"})
                return

            raw_fields = 0
            for pa in payload_analyses:
                flat = api_explorer.extract_field_paths(pa.get("analysis", {}))
                raw_fields += len(flat)
            yield _sse_event("step", {"phase": "payloads", "status": "done",
                                       "detail": f"Found {raw_fields} unique field paths in API response"})

            # Phase 2: RAG retrieval
            yield _sse_event("step", {"phase": "rag", "status": "running", "label": "Retrieving RAG context..."})
            await asyncio.sleep(0.05)  # flush so frontend shows RAG phase before work starts

            rag_context = await mapping_engine.analyze_rag(
                data_point_name=request.data_point_name,
                cmsd_entity=request.cmsd_entity,
                api_endpoint=", ".join(all_endpoints_str),
            )

            yield _sse_event("step", {"phase": "rag", "status": "done",
                                       "detail": f"Retrieved schema context for {request.cmsd_entity}"})

            # Phase 3: LLM analysis
            yield _sse_event("step", {"phase": "llm", "status": "running",
                                       "label": "Analyzing with LLM...",
                                       "detail": f"Sending {raw_fields} API fields to LLM for {request.cmsd_entity} mapping"})
            await asyncio.sleep(0.05)  # flush so frontend shows LLM phase before the (slow) LLM call

            if len(payload_analyses) == 1:
                mapping = await mapping_engine.propose_mapping(
                    data_point_name=request.data_point_name,
                    cmsd_entity=request.cmsd_entity,
                    api_endpoint=all_endpoints_str[0],
                    payload_analysis=payload_analyses[0]["analysis"],
                    rag_context=rag_context,
                )
            else:
                endpoint_labels = [pa["source_label"] for pa in payload_analyses]
                mapping = await mapping_engine.propose_mapping_multi(
                    data_point_name=request.data_point_name,
                    cmsd_entity=request.cmsd_entity,
                    endpoint_labels=endpoint_labels,
                    payload_analyses=payload_analyses,
                    rag_context=rag_context,
                )

            yield _sse_event("step", {"phase": "llm", "status": "done",
                                       "detail": f"{len(mapping.get('mapping', {}))} fields proposed"})

            # Phase 4: Done
            field_count = len(mapping.get("mapping", {}))
            yield _sse_event("result", {
                "success": True,
                "cmsd_entity": request.cmsd_entity,
                "mapping": mapping,
                "proposed_mapping": mapping,
                "rag_context": rag_context,
            })

        except Exception as e:
            logger.error(f"Streaming analysis failed: {e}\n{traceback.format_exc()}")
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/mapping/chat")
async def chat_mapping(request: MappingChatRequest):
    """Chat with the AI agent about a specific mapping."""
    try:
        response = await mapping_engine.chat_about_mapping(
            data_point_name=request.data_point_name,
            current_mapping=request.current_mapping,
            user_question=request.user_question,
        )
        return {"success": True, "response": response}
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {e}")

class ReviewReanalyzeRequest(BaseModel):
    current_mapping: dict[str, Any]
    flagged_fields: list[dict[str, str]] = []
    flagged_relations: list[dict[str, Any]] = []
    data_point_name: str = ""
    cmsd_entity: str = ""
    approved_payloads: list[ApprovedPayload] = []


@router.post("/mapping/review-reanalyze")
async def review_reanalyze(request: ReviewReanalyzeRequest):
    """
    Targeted reanalysis: only refine fields the user has flagged with comments.
    Approved/pending fields are preserved untouched.
    """
    try:
        payload_analyses = []
        for ap in request.approved_payloads:
            if ap.raw_payload is None:
                continue
            analysis = api_explorer.analyze_payload(ap.raw_payload)
            payload_analyses.append({
                "endpoint": ap.endpoint,
                "source_label": ap.label or ap.endpoint,
                "analysis": analysis,
                "raw_payload": ap.raw_payload,
            })

        rag_context = await mapping_engine.analyze_rag(
            data_point_name=request.data_point_name,
            cmsd_entity=request.cmsd_entity,
        )

        refined = await mapping_engine.review_reanalyze(
            data_point_name=request.data_point_name,
            cmsd_entity=request.cmsd_entity,
            current_mapping=request.current_mapping,
            flagged_fields=request.flagged_fields,
            flagged_relations=request.flagged_relations,
            payload_analyses=payload_analyses if payload_analyses else None,
            rag_context=rag_context,
        )

        changed_fields = [f["field"] for f in request.flagged_fields]
        return {
            "success": True,
            "refined_mapping": refined,
            "changed_fields": changed_fields,
        }
    except Exception as e:
        logger.error(f"Review reanalyze failed: {e}")
        raise HTTPException(500, f"Review reanalyze failed: {e}")


@router.post("/mapping/edit")
async def edit_mapping(request: MappingEditsRequest):
    """Apply user edits to a mapping proposal."""
    try:
        updated = mapping_engine.apply_user_edits(
            current_mapping=request.current_mapping,
            edits=request.edits,
        )
        return {"success": True, "updated_mapping": updated}
    except Exception as e:
        raise HTTPException(400, f"Edit failed: {e}")

@router.post("/mapping/smart-reanalyze")
async def smart_reanalyze(request: SmartReanalyzeRequest):
    """
    Smart reanalysis: refine mapping based on user guidance.
    Uses the user's chat input as context for targeted re-mapping.
    """
    try:
        # Fetch fresh payloads if endpoints provided
        payload_analyses = []
        if request.endpoints:
            for ep in request.endpoints:
                payload_result = await api_explorer.fetch_payload(
                    source_id=ep.source_id,
                    endpoint=ep.endpoint,
                    method=ep.method,
                )
                payload_analysis = api_explorer.analyze_payload(payload_result["payload"])
                payload_analyses.append({
                    "endpoint": ep.endpoint,
                    "source_label": ep.label or ep.endpoint,
                    "analysis": payload_analysis,
                    "raw_payload": payload_result["payload"],
                })

        # Get RAG context
        rag_context = await mapping_engine.analyze_rag(
            data_point_name=request.data_point_name,
            cmsd_entity=request.cmsd_entity,
        )

        refined = await mapping_engine.smart_reanalyze(
            data_point_name=request.data_point_name,
            cmsd_entity=request.cmsd_entity,
            current_mapping=request.current_mapping,
            user_guidance=request.user_guidance,
            payload_analyses=payload_analyses if payload_analyses else None,
            rag_context=rag_context,
        )

        return {"success": True, "refined_mapping": refined}
    except Exception as e:
        logger.error(f"Smart reanalyze failed: {e}")
        raise HTTPException(500, f"Smart reanalyze failed: {e}")


@router.post("/mapping/validate-types")
async def validate_mapping_types(request: dict):
    """Validate all fields in a mapping against CMSD type hints.
    Returns per-field pass/fail with deterministic fix suggestions."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from shared.coerce import validate_mapping_types as _validate

    mapping = request.get("mapping", {})
    entity_type = request.get("cmsd_entity", mapping.get("cmsd_entity", "Resource"))
    result = _validate(mapping, entity_type)
    return {"success": True, **result}


@router.get("/mapping/transformations")
async def get_transformations():
    """Return available transformation presets for the frontend."""
    return {"transformations": TRANSFORMATION_PRESETS}


class ApplyTransformationRequest(BaseModel):
    raw_value: Any  # Accept any type — LLM may output numbers; coerced to str in handler
    transformation: dict[str, Any] | None = None


@router.post("/mapping/apply-transformation")
async def apply_transformation(request: ApplyTransformationRequest):
    """Execute a deterministic transformation on a raw value. No LLM involved."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from shared.transform import execute_transformation
    raw_str = str(request.raw_value) if request.raw_value is not None else ""
    return execute_transformation(raw_str, request.transformation)


@router.post("/mapping/fetch")
async def fetch_endpoints(request: FetchEndpointsRequest):
    """
    Fetch raw JSON payloads from one or more API endpoints.
    Returns the payloads with metadata for display in the PayloadViewer.
    Supports partial success: each payload has its own status field.
    """
    if not request.endpoints:
        raise HTTPException(400, "No endpoints specified")

    async def _fetch_one(ep: EndpointSpec) -> dict:
        try:
            result = await asyncio.wait_for(
                api_explorer.fetch_payload(
                    source_id=ep.source_id,
                    endpoint=ep.endpoint,
                    method=ep.method,
                ),
                timeout=30,
            )
            return {
                "endpoint": ep.endpoint,
                "source_id": ep.source_id,
                "label": ep.label or ep.endpoint,
                "url": result["url"],
                "status": "success",
                "status_code": result["status_code"],
                "size_bytes": result["payload_size_bytes"],
                "raw_payload": result["payload"],
            }
        except asyncio.TimeoutError:
            logger.warning(f"Fetch timed out for {ep.source_id}{ep.endpoint}")
            return {
                "endpoint": ep.endpoint,
                "source_id": ep.source_id,
                "label": ep.label or ep.endpoint,
                "url": "",
                "status": "error",
                "error_message": "Request timed out after 30 seconds",
                "status_code": None,
                "size_bytes": 0,
                "raw_payload": None,
            }
        except Exception as e:
            logger.warning(f"Fetch failed for {ep.source_id}{ep.endpoint}: {e}")
            return {
                "endpoint": ep.endpoint,
                "source_id": ep.source_id,
                "label": ep.label or ep.endpoint,
                "url": "",
                "status": "error",
                "error_message": str(e),
                "status_code": None,
                "size_bytes": 0,
                "raw_payload": None,
            }

    payloads = await asyncio.gather(
        *[_fetch_one(ep) for ep in request.endpoints]
    )

    return {"success": True, "payloads": list(payloads)}


# ─── Mapping Queue (staged batch generation) ─────────────────

# In-memory queue: mapping_id → {mapping_data, confirmed_at, ...}
_mapping_queue: dict[str, dict] = {}

# Track whether code has been generated (but not yet applied)
_generated_diff: dict | None = None
_generation_report: dict | None = None
_generation_branch: str = "feature/agentic-rag"


def _mappings_dir() -> str:
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".agent-mappings")
    os.makedirs(d, exist_ok=True)
    return d


def _normalize_api_paths(mapping: dict) -> dict:
    """
    Strip the count_path array prefix from every api_path so all paths
    are instance-relative. Called before saving a confirmed mapping.

    Handles any nesting depth — generic across all API response structures:
      $.resources[*].identifier        → identifier
      $.d.results[*].ObjectID          → ObjectID
      $.data.orders[*].status          → status
      resources[*].name                 → name
      resources.0.name                  → name
      name                              → name (already relative)
    """
    import re
    count_path = mapping.get("instances", {}).get("count_path", "")
    if not count_path:
        return mapping

    # Extract all path segments before the [*] array indicator.
    # $.d.results[*] → ["d", "results"]; $.resources[*] → ["resources"]
    cleaned = count_path.replace("$.", "", 1) if count_path.startswith("$.") else count_path
    cleaned = cleaned.replace("[*]", "")
    prefix_segments = [p for p in cleaned.split(".") if p]
    if not prefix_segments:
        return mapping

    # Build regex to strip the full array prefix, with optional [*] or digit
    # index between each segment. e.g. for ["d", "results"]:
    #   ^d\.(?:\[[*]\]|\d+)?\.results\.(?:\[[*]\]|\d+)?\.
    prefix_pattern = ""
    for seg in prefix_segments:
        prefix_pattern += re.escape(seg) + r'\.(?:\[[*]\]|\d+)?\.'
    # Make the final dot optional (path may not have trailing dot)
    prefix_pattern += "?"
    strip_re = re.compile('^' + prefix_pattern)

    field_mappings = mapping.get("mapping", {})
    for cmsd_field, field_info in field_mappings.items():
        if not isinstance(field_info, dict):
            continue
        api_path = field_info.get("api_path", "")
        if not api_path:
            continue

        # Strip leading "$." if present
        normalized = api_path.replace("$.", "", 1) if api_path.startswith("$.") else api_path

        # Strip the full array prefix (all nesting levels)
        normalized = strip_re.sub('', normalized, count=1)
        if normalized and normalized != api_path:
            field_info["api_path"] = normalized

    return mapping


@router.post("/mappings/manual")
async def create_manual_mapping(request: dict):
    """
    Create a manual (non-API) mapping for an entity type. Used when referenced
    entity instances are missing (e.g. no API provides ResourceClass data).
    """
    import time
    from datetime import datetime, timezone
    from .cmsd_catalog import get_catalog

    catalog = get_catalog()
    entity_type = request.get("entity_type", "")
    if entity_type not in catalog.get("entities", {}):
        raise HTTPException(400, f"Unknown entity type: {entity_type}")

    entries: list[dict] = request.get("entries", [])
    if not entries:
        raise HTTPException(400, "At least one entry is required")

    data_point = request.get("data_point", f"manual-{entity_type.lower()}")

    # Build raw_payload from entries (each entry must have at least 'identifier')
    raw_payload = []
    for entry in entries:
        if "identifier" not in entry:
            raise HTTPException(400, "Each entry must have an 'identifier' field")
        raw_payload.append(entry)

    # Build field mappings: every key in the first entry maps 1:1 (relative paths)
    field_map = {}
    for key in entries[0].keys():
        field_map[key] = {
            "api_path": key,
            "type_conversion": "none",
            "sample_value": entries[0][key],
            "confidence": "high",
            "status": "approved",
        }

    mapping_id = f"manual-{entity_type.lower()}-{int(time.time() * 1000)}"
    mapping = {
        "data_point": data_point,
        "data_point_name": data_point,
        "cmsd_entity": entity_type,
        "source": {"type": "manual"},
        "endpoints": [
            {
                "endpoint": "(manual)",
                "source_id": "manual",
                "label": data_point,
                "raw_payload": raw_payload,
            }
        ],
        "mapping": field_map,
        "relations": [],
        "notes": f"Manual entries for {entity_type} — {len(entries)} instance(s).",
        "requires_manual_review": False,
    }

    filepath = os.path.join(_mappings_dir(), f"{mapping_id}.json")
    mapping["confirmed_at"] = datetime.now(timezone.utc).isoformat()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, default=str)

    _mapping_queue[mapping_id] = {
        "mapping_id": mapping_id,
        "confirmed_at": mapping["confirmed_at"],
        "mapping": mapping,
        "data_point": data_point,
        "cmsd_entity": entity_type,
    }

    logger.info(f"Manual mapping created: {mapping_id} ({entity_type}, {len(entries)} entries)")
    return {
        "success": True,
        "mapping_id": mapping_id,
        "cmsd_entity": entity_type,
        "instance_count": len(entries),
        "message": f"Manual {entity_type} mapping created with {len(entries)} instance(s)",
    }


@router.put("/mapping/{mapping_id}/confirm")
async def confirm_mapping(mapping_id: str, request: dict):
    """
    Confirm a mapping → save to .agent-mappings/ with resolved source config.
    Bakes the source URL + auth into the mapping so the runtime factory can fetch APIs.
    Normalizes api_path values to be instance-relative.
    """
    import time
    from datetime import datetime, timezone

    mapping = request.get("mapping", {})
    approved_payloads = request.get("approved_payloads", [])

    # Resolve source_id from approved payloads or mapping
    source_id = mapping.get("source_id", "")
    if not source_id and approved_payloads:
        source_id = approved_payloads[0].get("source_id", "")

    # Resolve source config from connection manager
    source = {}
    if source_id:
        source = connection_manager.get_source(source_id) or {}

    # Bake source block into mapping (use resolved base_url)
    # Use the endpoint from approved_payloads (it's the actual API path like /resources)
    endpoint = ""
    if approved_payloads:
        endpoint = approved_payloads[0].get("endpoint", "")
    if not endpoint:
        endpoint = mapping.get("endpoint", mapping.get("api_endpoint", ""))

    # Resolve + (optionally) encrypt the source auth. The connection_manager stores
    # flat auth_type/username/password; normalize_auth maps those into the {type,...}
    # shape that cmsd_twin_service.api_client._build_auth_headers reads. When
    # SAP_CRED_KEY is set, the normalized auth is encrypted into auth_encrypted
    # (a Fernet token at rest) and the plaintext `auth` key is omitted; otherwise we
    # fall back to a plaintext normalized `auth` block (dev / no-key mode). This also
    # fixes the previous bug where `source.get("auth", {"type":"none"})` always
    # returned {"type":"none"} (sources have no `auth` key), silently breaking real
    # SAP Basic auth while appearing to work for the unauthenticated mock SAP.
    from shared.odata.auth import normalize_auth
    norm_auth = normalize_auth(source)
    auth_encrypted = None
    if os.getenv("SAP_CRED_KEY"):
        try:
            from shared.crypto import encrypt_dict
            auth_encrypted = encrypt_dict(norm_auth)
        except Exception as e:
            logger.warning(f"auth encryption failed for {mapping_id}, storing plaintext: {e}")
    mapping["source"] = {
        "type": mapping.get("source_type", "generic"),
        "base_url": source.get("base_url", ""),
        "endpoint": endpoint,
        "method": mapping.get("method", "GET"),
        "auth_encrypted": auth_encrypted,
        "auth": norm_auth if auth_encrypted is None else None,
        "headers": mapping.get("source_headers", source.get("extra_headers", {}) or {}),
        "params": mapping.get("source_params", {}) or {},
    }

    # Store endpoint/payload info for edit restoration
    mapping["endpoints"] = approved_payloads

    # Normalize api_paths (strip count_path array prefix)
    mapping = _normalize_api_paths(mapping)

    # Stamp all fields as approved (they were approved to reach confirm)
    field_map = mapping.get("mapping", {})
    for field_name, field_info in field_map.items():
        if isinstance(field_info, dict) and not field_info.get("status"):
            field_info["status"] = "approved"

    # Save to disk (persistent) — use clean filename: {mapping_id}.json
    filepath = os.path.join(_mappings_dir(), f"{mapping_id}.json")
    mapping["confirmed_at"] = datetime.now(timezone.utc).isoformat()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, default=str)

    # Add to in-memory queue
    mapping_data = {
        "mapping_id": mapping_id,
        "confirmed_at": mapping["confirmed_at"],
        "mapping": mapping,
        "data_point": mapping.get("data_point", mapping.get("data_point_name", "unknown")),
        "cmsd_entity": mapping.get("cmsd_entity", "unknown"),
    }
    _mapping_queue[mapping_id] = mapping_data

    field_map = mapping.get("mapping", {})
    approved = sum(1 for f in field_map.values() if isinstance(f, dict) and f.get("status") == "approved")

    logger.info(f"Mapping confirmed: {mapping_id} → {mapping.get('cmsd_entity', '?')} ({len(field_map)} fields)")
    return {
        "success": True,
        "mapping_id": mapping_id,
        "cmsd_entity": mapping.get("cmsd_entity", ""),
        "field_count": len(field_map),
        "approved_count": approved,
        "message": f"Mapping confirmed for {mapping.get('cmsd_entity', 'entity')}",
    }


@router.get("/mapping/queue")
async def get_mapping_queue():
    """List all confirmed mappings waiting for code generation."""
    items = []
    for mid, data in _mapping_queue.items():
        items.append({
            "mapping_id": mid,
            "confirmed_at": data.get("confirmed_at"),
            "data_point": data.get("data_point"),
            "cmsd_entity": data.get("cmsd_entity"),
        })
    return {"queue_size": len(items), "mappings": items}


@router.delete("/mapping/queue/{mapping_id}")
async def remove_from_queue(mapping_id: str):
    """Remove a mapping from the generation queue."""
    if mapping_id not in _mapping_queue:
        raise HTTPException(404, f"Mapping '{mapping_id}' not in queue")
    del _mapping_queue[mapping_id]
    import os
    for fname in os.listdir(_mappings_dir()):
        if fname.startswith(mapping_id):
            os.remove(os.path.join(_mappings_dir(), fname))
    logger.info(f"Mapping removed from queue: {mapping_id}")
    return {"success": True, "queue_size": len(_mapping_queue)}


@router.put("/mapping/queue/{mapping_id}")
async def edit_queued_mapping(mapping_id: str, request: dict):
    """Edit a queued mapping before generation."""
    if mapping_id not in _mapping_queue:
        raise HTTPException(404, f"Mapping '{mapping_id}' not in queue")
    import time
    _mapping_queue[mapping_id].update({
        "mapping": request.get("mapping", _mapping_queue[mapping_id].get("mapping", {})),
        "cmsd_schema_context": request.get("cmsd_schema_context", _mapping_queue[mapping_id].get("cmsd_schema_context", "")),
        "edited_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    # Re-persist
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{mapping_id}_{timestamp}.json"
    filepath = os.path.join(_mappings_dir(), filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(_mapping_queue[mapping_id], f, indent=2, default=str)
    return {"success": True, "mapping": _mapping_queue[mapping_id]}


# ─── Confirmed Mappings (Review Queue) ─────────────────────


@router.get("/mappings")
async def list_mappings():
    """List all confirmed mappings from .agent-mappings/"""
    mappings = []
    mappings_dir = _mappings_dir()
    if os.path.isdir(mappings_dir):
        for filename in sorted(os.listdir(mappings_dir)):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(mappings_dir, filename)
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                field_map = data.get("mapping", {})
                approved = sum(1 for f in field_map.values()
                               if isinstance(f, dict) and f.get("status", "approved") != "flagged")
                flagged = sum(1 for f in field_map.values()
                              if isinstance(f, dict) and f.get("status") == "flagged")
                relations = data.get("relations", [])
                relation_targets = []
                if isinstance(relations, list):
                    for r in relations:
                        if isinstance(r, dict) and r.get("target_entity"):
                            relation_targets.append(r["target_entity"])
                mappings.append({
                    "id": filename.replace(".json", ""),
                    "data_point": data.get("data_point", data.get("data_point_name", "")),
                    "cmsd_entity": data.get("cmsd_entity", ""),
                    "source": data.get("source", {}),
                    "instances": data.get("instances", {}),
                    "field_count": len(field_map),
                    "approved_count": approved,
                    "flagged_count": flagged,
                    "relation_count": len(relations) if isinstance(relations, list) else 0,
                    "relation_targets": relation_targets,
                    "confirmed_at": data.get("confirmed_at", ""),
                })
            except Exception as e:
                logger.warning(f"Failed to read mapping {filename}: {e}")
    return {"mappings": mappings}


@router.get("/mappings/{mapping_id}")
async def get_mapping(mapping_id: str):
    """Get a single confirmed mapping by ID (full data for editing)."""
    filepath = os.path.join(_mappings_dir(), f"{mapping_id}.json")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Mapping not found")
    with open(filepath, "r") as f:
        data = json.load(f)
    data["id"] = mapping_id
    return data


@router.delete("/mappings/{mapping_id}")
async def delete_mapping(mapping_id: str):
    """Delete a confirmed mapping."""
    filepath = os.path.join(_mappings_dir(), f"{mapping_id}.json")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Mapping not found")
    os.remove(filepath)
    # Also remove from in-memory queue if present
    _mapping_queue.pop(mapping_id, None)
    return {"success": True, "message": f"Mapping {mapping_id} deleted"}


CMSD_ENTITIES = [
    "Resource", "ResourceClass", "PartType", "Part", "BillOfMaterials",
    "BillOfMaterialsComponent", "ProcessPlan", "Process", "Order", "OrderLine",
    "Calendar", "Shift", "Break", "Holiday", "Connection",
    "Job", "InventoryItem", "MaintenancePlan",
]

# In V1, all CMSD entities are independent at the top level because
# cross-entity references live in nested objects (out of scope for V1).
# Dependencies come from API field naming conventions at mapping time.
INDEPENDENT_ENTITIES = set(CMSD_ENTITIES)


def _infer_deps_from_fields(cmsd_entity: str, field_map: dict) -> list[str]:
    """Infer cross-entity dependencies from field naming conventions."""
    deps = set()
    for field_name in field_map:
        if field_name.endswith("_id"):
            entity_hint = (
                field_name.replace("_id", "")
                .replace("_", " ")
                .title()
                .replace(" ", "")
            )
            if entity_hint in CMSD_ENTITIES and entity_hint != cmsd_entity:
                deps.add(entity_hint)
    return sorted(deps)


@router.post("/mapping/infer-dependencies")
async def infer_dependencies(body: dict):
    """Infer cross-entity dependencies for an in-progress mapping.
    Uses naming conventions ({entity}_id -> {Entity}) and the list of
    known independent entities. Returns both inferred dependencies and
    whether this entity is ready to map (all deps are independent or
    already have confirmed mappings)."""
    cmsd_entity = body.get("cmsd_entity", "")
    field_map = body.get("mapping", {})

    inferred = _infer_deps_from_fields(cmsd_entity, field_map)
    is_independent = cmsd_entity in INDEPENDENT_ENTITIES and len(inferred) == 0

    return {
        "entity": cmsd_entity,
        "dependencies": inferred,
        "is_independent": is_independent,
        "independent_entities": sorted(INDEPENDENT_ENTITIES),
        "all_entities": CMSD_ENTITIES,
    }


# ─── CMSD Catalog ────────────────────────────────────────────

@router.get("/cmsd-catalog")
async def get_cmsd_catalog():
    """
    Return CMSD entity catalog with human-readable metadata.
    Introspects actual CMSD Pydantic models — always in sync with the schema.
    Used by frontend to show rich entity descriptions, field requirements,
    reference paths, and examples in the MappingWizard entity picker.
    """
    try:
        from .cmsd_catalog import get_catalog
        return get_catalog()
    except Exception as e:
        logger.error(f"Failed to build CMSD catalog: {e}")
        raise HTTPException(500, f"Catalog build failed: {e}")


# ─── Code Generation Pipeline ───────────────────────────────

@router.post("/code-generation/generate")
async def trigger_code_generation():
    """
    Trigger the 3-agent code generation pipeline on ALL queued mappings.
    Writes to a feature branch (does NOT merge to main yet).
    Returns a diff + full agent report for user review.
    """
    global _generated_diff, _generation_report

    if not _mapping_queue:
        raise HTTPException(400, "No mappings in queue. Confirm at least one mapping first.")

    if not llm_client.get_config().get("connected", False):
        raise HTTPException(400, "No LLM connected. Please connect an LLM provider first.")

    from .code_generation.orchestrator import code_gen_orchestrator

    try:
        # Read current twin code files
        existing_code = _read_existing_twin_code()

        # Run batch generation on all queued mappings
        report = await code_gen_orchestrator.generate_batch(
            mappings=list(_mapping_queue.values()),
            existing_code=existing_code,
        )

        # Get the unified diff (git Manager writes files to feature branch)
        from .code_generation.git_manager import git_manager
        diff_result = git_manager.get_diff_last_commit()
        diff_text = diff_result.get("diff", "")

        # Also get full feature-branch diff vs main
        rc, diff_vs_main, _ = git_manager._run_git("diff", "main", git_manager.FEATURE_BRANCH)
        if rc != 0:
            # Fallback: diff vs HEAD~1
            rc, diff_vs_main, _ = git_manager._run_git("diff", "HEAD~1", "HEAD")

        _generated_diff = {
            "files_changed": report.get("files_generated", []),
            "unified_diff": diff_vs_main or diff_text,
            "branch": _generation_branch,
        }
        _generation_report = report

        return {
            "success": True,
            "message": "Code generated on feature branch. Review the diff before applying.",
            "report": report,
            "diff": _generated_diff,
            "next_actions": ["Review diff", "POST /code-generation/apply to merge", "POST /code-generation/rollback to discard"],
        }
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        raise HTTPException(500, f"Code generation failed: {e}")


@router.post("/code-generation/apply")
async def apply_code_generation():
    """
    Apply the generated code: merge feature branch → main.
    Signals the CMSD twin service to reload (if running with --reload).
    """
    global _generated_diff, _generation_report, _mapping_queue

    if not _generated_diff:
        raise HTTPException(400, "No generated code to apply. Run /code-generation/generate first.")

    from .code_generation.git_manager import git_manager

    try:
        # Merge feature branch into main
        branch_ok = git_manager.ensure_feature_branch()
        if not branch_ok.get("ok"):
            raise RuntimeError(f"Branch error: {branch_ok.get('error')}")

        # Checkout main and merge
        rc, _, err = git_manager._run_git("checkout", "main")
        if rc != 0:
            raise RuntimeError(f"Failed to checkout main: {err}")

        rc, _, err = git_manager._run_git("merge", _generation_branch, "--no-ff", "-m",
                                          "[AGENT] Apply batch mapping generation")
        if rc != 0:
            # Abort merge
            git_manager._run_git("merge", "--abort")
            git_manager._run_git("checkout", _generation_branch)
            raise RuntimeError(f"Merge conflict — auto-aborted: {err}")

        # Clear state
        commit = _generation_report.get("git", {}).get("commit_hash", "N/A") if _generation_report else "N/A"
        files_changed = _generated_diff.get("files_changed", [])

        # Clear queue after successful apply
        _mapping_queue.clear()
        _generated_diff = None
        _generation_report = None

        logger.info(f"Code generation applied: {commit}")
        return {
            "success": True,
            "message": "Generated code merged to main. CMSD twin service will reload on next file change.",
            "commit_hash": commit,
            "files_changed": files_changed,
        }
    except Exception as e:
        logger.error(f"Apply failed: {e}")
        raise HTTPException(500, f"Apply failed: {e}")


@router.post("/code-generation/rollback")
async def rollback_code_generation():
    """Discard the generated code and return to main branch."""
    global _generated_diff, _generation_report

    from .code_generation.git_manager import git_manager

    try:
        git_manager.ensure_feature_branch()
        git_manager._run_git("checkout", "main")
        git_manager._run_git("branch", "-D", _generation_branch)

        _generated_diff = None
        _generation_report = None

        logger.info("Code generation rolled back — feature branch deleted")
        return {
            "success": True,
            "message": "Generated code discarded. Mapping queue preserved.",
        }
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        raise HTTPException(500, f"Rollback failed: {e}")


@router.get("/code-generation/diff")
async def get_generation_diff():
    """Get the current generated (unapplied) diff for review."""
    if not _generated_diff:
        raise HTTPException(404, "No generated code to review. Run /code-generation/generate first.")
    return _generated_diff


@router.get("/code-generation/status")
async def get_generation_status():
    """Check whether code has been generated and is pending apply."""
    return {
        "has_generated_code": _generated_diff is not None,
        "has_report": _generation_report is not None,
        "queue_size": len(_mapping_queue),
        "generation_branch": _generation_branch,
        "files_changed": _generated_diff.get("files_changed", []) if _generated_diff else [],
    }


# ─── Git helpers (already used above via git_manager) ───────

def _read_existing_twin_code() -> dict[str, str]:
    """Read current api_client.py and factory.py from the CMSD twin service."""
    import os
    twin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cmsd_twin_service")
    code = {}
    for fname in ("api_client.py", "factory.py"):
        fpath = os.path.join(twin_dir, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    code[fname] = f.read()
            except Exception:
                code[fname] = ""
        else:
            code[fname] = ""
    return code


def _truncate_payload(payload: Any, max_size: int = 5000) -> Any:
    """Truncate a JSON payload to max_size bytes for display, preserving structure."""
    serialized = json.dumps(payload, indent=2, default=str)
    if len(serialized) <= max_size:
        return payload
    # Truncate: keep first part of the serialized version
    truncated_str = serialized[:max_size] + "\n... (truncated)"
    return {"_truncated": True, "_preview": truncated_str, "_full_size_bytes": len(serialized)}


# ─── Git status (for UI) ────────────────────────────────────

@router.get("/git/status")
async def get_git_status():
    """Get current git branch and status."""
    from .code_generation.git_manager import git_manager
    if not git_manager._git_repo:
        return {"has_git": False}
    rc, branch, _ = git_manager._run_git("branch", "--show-current")
    rc2, status, _ = git_manager._run_git("status", "--short")
    return {
        "has_git": True,
        "branch": branch,
        "status": status,
        "repo_root": git_manager._git_repo,
    }


@router.get("/git/diff")
async def get_git_diff():
    """Get unified diff of current working tree vs HEAD."""
    from .code_generation.git_manager import git_manager
    if not git_manager._git_repo:
        raise HTTPException(404, "Not a git repository")
    rc, diff, err = git_manager._run_git("diff", "HEAD")
    return {"diff": diff, "error": err if rc != 0 else None}


@router.post("/git/rollback")
async def rollback_git():
    """Revert the last commit (on feature branch only)."""
    from .code_generation.git_manager import git_manager
    result = git_manager.revert_last_commit()
    if not result.get("reverted"):
        raise HTTPException(400, result.get("error", "Rollback failed"))
    return result
