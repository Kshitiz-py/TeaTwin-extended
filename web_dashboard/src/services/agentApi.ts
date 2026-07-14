const BASE = '/api/agent/v1';

// ─── Agent Status ──────────────────────────────────────────

export interface AgentStatus {
  connected: boolean;
  provider_type?: string;
  host?: string;
  chat_model?: string;
  embed_model?: string;
  has_api_key?: boolean;
  embed_provider?: string | { provider_type: string; host: string; chat_model: string; embed_model: string; has_api_key: boolean };
}

// ─── Provider Configuration ─────────────────────────────────

export interface ProviderConfig {
  provider_type: string;
  host: string;
  api_key: string;
  chat_model: string;
  embed_model: string;
}

export interface MultiProviderConfig {
  chat: ProviderConfig;
  embed?: ProviderConfig;
}

export interface ProviderInfo {
  name: string;
  label: string;
  api_style: string;
  host: string;
  chat_model: string;
  embed_model: string;
  has_embeddings: boolean;
  requires_api_key: boolean;
  description: string;
}

export interface ProviderListResponse {
  providers: ProviderInfo[];
}

export interface ConnectionTestResult {
  ok: boolean;
  message?: string;
  models?: string[];
  error?: string;
}

// ─── Mapping Queue ─────────────────────────────────────────

export interface QueuedMapping {
  mapping_id: string;
  confirmed_at: string;
  data_point: string;
  cmsd_entity: string;
}

export interface MappingQueueResponse {
  queue_size: number;
  mappings: QueuedMapping[];
}

// ─── Multi-Endpoint Support ────────────────────────────────

export interface EndpointInput {
  sourceId: string;
  endpoint: string;
}

// ─── Fetch Endpoints (Payload Viewer) ──────────────────────

export interface FetchEndpointSpec {
  source_id: string;
  endpoint: string;
  method: string;
  label: string;
}

export interface FetchedPayload {
  endpoint: string;
  source_id: string;
  label: string;
  url: string;
  status: 'success' | 'error';
  error_message?: string;
  status_code: number | null;
  size_bytes: number;
  raw_payload: any;
}

export interface FetchEndpointsResponse {
  success: boolean;
  payloads: FetchedPayload[];
}

// ─── SAP OData Discovery ───────────────────────────────────

export interface DiscoveredEntitySet {
  name: string;
  entity_type: string;
  sap_label: string;
  key_fields: string[];
  property_count: number;
  navigation_count: number;
}

export interface DiscoverResponse {
  success: boolean;
  source_schema_id: string;
  entity_sets: DiscoveredEntitySet[];
  chunks_indexed: number;
}

export interface ODataPropertyInfo {
  name: string;
  type: string;
  nullable: boolean;
  is_key: boolean;
  sap_label: string;
  sap_unit: string;
  sap_semantics: string;
  max_length: number | null;
}

export interface ODataNavigationInfo {
  name: string;
  to_entity_type: string;
  from_role: string;
  to_role: string;
  relationship: string;
  referential_constraints: [string, string][];
}

export interface ODataEntityTypeInfo {
  name: string;
  entity_set_name: string;
  properties: ODataPropertyInfo[];
  keys: string[];
  navigation_properties: ODataNavigationInfo[];
  sap_label: string;
}

export interface SourceSchemaResponse {
  source_schema: {
    service_url: string;
    namespace: string;
    entity_types: ODataEntityTypeInfo[];
  };
}

export interface CoveringEndpoint {
  entity_set: string;
  endpoint: string;
  role: string;
  key_field: string;
  count_path: string;
}

export interface FieldAttribution {
  [cmsd_field: string]: {
    entity_set: string;
    property: string;
    confidence: string;
    transform?: string;
    unit_from_field?: { unit_path: string; target_unit: string };
  };
}

export interface RecommendDebug {
  system_prompt: string;
  user_prompt: string;
  candidates: Record<string, Array<{ entity_set: string; entity_type: string; score: number; content: string }>>;
  raw_response: string;
  model: string;
  provider: string;
}

export interface RecommendResponse {
  cmsd_entity: string;
  covering_endpoints: CoveringEndpoint[];
  field_attribution: FieldAttribution;
  join_keys: { from: { entity_set: string; property: string }; to: { entity_set: string; property: string }; via_nav: string }[];
  coverage_gaps: string[];
  proposed_relations: any[];
  notes?: string;
  debug?: RecommendDebug;
}

export interface SampleResponse {
  rows: any[];
  count: number;
  entity_set: string;
}

export interface AnalyzeMappingMultiRequest {
  endpoints: EndpointInput[];
  data_point_name: string;
  cmsd_entity: string;
}

// ─── Smart Reanalyze ───────────────────────────────────────

export interface SmartReanalyzeRequest {
  data_point_name: string;
  cmsd_entity: string;
  current_mapping: Record<string, any>;
  user_guidance: string;
  endpoints?: EndpointInput[];
}

// ─── Confirmed Mappings (Review Queue) ─────────────────────

export interface MappingSummary {
  id: string;
  data_point: string;
  cmsd_entity: string;
  source: { base_url: string; endpoint: string; method: string; auth?: any };
  instances: { count_path: string; key_field: string };
  field_count: number;
  approved_count: number;
  flagged_count: number;
  relation_count?: number;
  relation_targets?: string[];
  confirmed_at: string;
}

// ─── Code Generation ───────────────────────────────────────

export interface CodeGenerationReport {
  success: boolean;
  batch_size: number;
  files_generated: string[];
  reports: GenerationMappingReport[];
  git: {
    committed: boolean;
    commit_hash: string | null;
    error?: string;
  };
  elapsed_seconds: number;
  timestamp: string;
}

export interface GenerationMappingReport {
  mapping_id: string;
  success: boolean;
  data_point: string;
  cmsd_entity: string;
  writer: Record<string, unknown>;
  reviewer: Record<string, unknown>;
  tester: Record<string, unknown>;
  git: Record<string, unknown>;
  elapsed_seconds: number;
  timestamp: string;
  error?: string;
}

export interface GeneratedDiff {
  files_changed: string[];
  unified_diff: string;
  branch: string;
}

export interface GenerationStatus {
  has_generated_code: boolean;
  has_report: boolean;
  queue_size: number;
  generation_branch: string;
  files_changed: string[];
}

export interface ApplyResult {
  success: boolean;
  message: string;
  commit_hash: string;
  files_changed: string[];
}

export interface GitStatus {
  has_git?: boolean;
  branch?: string;
  status?: string;
  repo_root?: string;
}

// ─── API Client ─────────────────────────────────────────────

export const agentApi = {
  // Agent Connection
  async getAgentStatus(): Promise<AgentStatus> {
    const res = await fetch(`${BASE}/agent/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async connectAgent(config: MultiProviderConfig, timeoutSeconds?: number) {
    const url = timeoutSeconds
      ? `${BASE}/agent/connect?timeout=${timeoutSeconds}`
      : `${BASE}/agent/connect`;
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async disconnectAgent() {
    const res = await fetch(`${BASE}/agent/disconnect`, { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async testAgent() {
    const res = await fetch(`${BASE}/agent/test`, { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async listProviders(): Promise<ProviderListResponse> {
    const res = await fetch(`${BASE}/agent/providers`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async listModels(): Promise<{ models: { id: string; name: string }[] }> {
    const res = await fetch(`${BASE}/agent/models`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // Sources
  async createSource(body: any) {
    const res = await fetch(`${BASE}/sources`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async getSources() {
    const res = await fetch(`${BASE}/sources`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async getSource(id: string) {
    const res = await fetch(`${BASE}/sources/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async testSource(id: string) {
    const res = await fetch(`${BASE}/sources/${id}/test`, { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async deleteSource(id: string) {
    const res = await fetch(`${BASE}/sources/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // SAP OData Discovery — deterministic; the LLM never connects to SAP.
  async discoverSchema(sourceId: string, entitySetFilter?: string[]): Promise<DiscoverResponse> {
    const res = await fetch(`${BASE}/sources/${sourceId}/discover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entity_set_filter: entitySetFilter ?? null }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async getSourceSchema(sourceId: string, entitySet?: string): Promise<SourceSchemaResponse> {
    const url = entitySet
      ? `${BASE}/sources/${sourceId}/schema?entity_set=${encodeURIComponent(entitySet)}`
      : `${BASE}/sources/${sourceId}/schema`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async sampleEntitySet(sourceId: string, entitySet: string, top = 3): Promise<SampleResponse> {
    const res = await fetch(`${BASE}/sources/${sourceId}/sample`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entity_set: entitySet, top }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // Endpoint recommendation — LLM-over-RAG (metadata only).
  async recommendEndpoints(sourceId: string, cmsdEntity: string): Promise<RecommendResponse> {
    const res = await fetch(`${BASE}/mapping/recommend-endpoints`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_id: sourceId, cmsd_entity: cmsdEntity }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // RAG
  async indexRag() {
    const res = await fetch(`${BASE}/rag/index`, { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async getRagStats() {
    const res = await fetch(`${BASE}/rag/stats`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // Mapping — Fetch Raw Payloads
  async fetchEndpoints(endpoints: FetchEndpointSpec[]): Promise<FetchEndpointsResponse> {
    const res = await fetch(`${BASE}/mapping/fetch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ endpoints }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // Mapping — Single Endpoint
  async analyzeMapping(body: any) {
    const res = await fetch(`${BASE}/mapping/analyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // Streaming version — returns an abortable fetch for SSE consumption
  analyzeMappingStream(body: any, onStep: (step: any) => void, onResult: (result: any) => void, onError: (msg: string) => void): AbortController {
    const controller = new AbortController();
    let resultReceived = false;

    // Hard timeout — prevents infinite spinner
    const timeout = setTimeout(() => {
      if (!resultReceived) {
        controller.abort();
        onError('Analysis timed out after 120s. The LLM may be overloaded — try again.');
      }
    }, 120000);

    fetch(`${BASE}/mapping/analyze-stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    }).then(async (res) => {
      if (!res.ok) { onError(`HTTP ${res.status}`); return; }
      const reader = res.body?.getReader();
      if (!reader) { onError('No response stream'); return; }
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (value) {
          buffer += decoder.decode(value, { stream: true });
        }

        // Split on \n\n (SSE message delimiter) — each chunk is a complete event
        const messages = buffer.split('\n\n');
        buffer = messages.pop() || ''; // keep incomplete message for next read

        for (const msg of messages) {
          if (!msg.trim()) continue;
          const lines = msg.split('\n');
          let eventType = '';
          for (const line of lines) {
            if (line.startsWith('event: ')) eventType = line.slice(7).trim();
            else if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (eventType === 'step') onStep(data);
                else if (eventType === 'result') { onResult(data); resultReceived = true; }
                else if (eventType === 'error') onError(data.message);
              } catch (e) {
                console.error('SSE parse error:', e, 'line:', line.slice(0, 100));
              }
            }
          }
        }

        if (done) {
          // Process final incomplete message if it has both event and data
          if (buffer.trim()) {
            const lines = buffer.split('\n');
            let eventType = '';
            for (const line of lines) {
              if (line.startsWith('event: ')) eventType = line.slice(7).trim();
              else if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6));
                  if (eventType === 'result') { onResult(data); resultReceived = true; }
                } catch { /* final chunk incomplete, ignore */ }
              }
            }
          }
          break;
        }
      }
    }).catch((e) => {
      if (e.name !== 'AbortError') onError(e.message || 'Stream failed');
    }).finally(() => {
      clearTimeout(timeout);
    });
    return controller;
  },
  // Mapping — Multi-Endpoint
  async analyzeMappingMulti(body: AnalyzeMappingMultiRequest) {
    const res = await fetch(`${BASE}/mapping/analyze-multi`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async chatMapping(body: any) {
    const res = await fetch(`${BASE}/mapping/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async editMapping(body: any) {
    const res = await fetch(`${BASE}/mapping/edit`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // Transformation Execution (deterministic, no LLM)
  async applyTransformation(rawValue: string, transformation: any): Promise<{ converted_value: string | null; success: boolean; error?: string }> {
    const res = await fetch(`${BASE}/mapping/apply-transformation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw_value: rawValue, transformation }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // Review Reanalyze (per-field flagged reanalysis)
  async reviewReanalyze(body: {
    current_mapping: Record<string, any>;
    flagged_fields: { field: string; comment: string }[];
    data_point_name: string;
    cmsd_entity: string;
    approved_payloads: any[];
  }) {
    const res = await fetch(`${BASE}/mapping/review-reanalyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // Smart Reanalyze
  async smartReanalyze(body: SmartReanalyzeRequest) {
    const res = await fetch(`${BASE}/mapping/smart-reanalyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // Mapping Queue (batch)
  async confirmMapping(id: string, body: any): Promise<{ success: boolean; mapping_id: string; cmsd_entity: string; field_count: number; approved_count: number; message: string }> {
    const res = await fetch(`${BASE}/mapping/${id}/confirm`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async getMappingQueue(): Promise<MappingQueueResponse> {
    const res = await fetch(`${BASE}/mapping/queue`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async removeFromQueue(mappingId: string) {
    const res = await fetch(`${BASE}/mapping/queue/${mappingId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async editQueuedMapping(mappingId: string, body: any) {
    const res = await fetch(`${BASE}/mapping/queue/${mappingId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async getMappingProgress() {
    const res = await fetch(`${BASE}/mapping/progress`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // Code Generation Pipeline
  async triggerCodeGeneration(): Promise<{ success: boolean; message: string; report: CodeGenerationReport; diff: GeneratedDiff }> {
    const res = await fetch(`${BASE}/code-generation/generate`, { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async applyCodeGeneration(): Promise<ApplyResult> {
    const res = await fetch(`${BASE}/code-generation/apply`, { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async rollbackCodeGeneration() {
    const res = await fetch(`${BASE}/code-generation/rollback`, { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async getGenerationDiff(): Promise<GeneratedDiff> {
    const res = await fetch(`${BASE}/code-generation/diff`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async getGenerationStatus(): Promise<GenerationStatus> {
    const res = await fetch(`${BASE}/code-generation/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // Git
  async getGitDiff() {
    const res = await fetch(`${BASE}/git/diff`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async rollbackGit() {
    const res = await fetch(`${BASE}/git/rollback`, { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async getGitStatus(): Promise<GitStatus> {
    const res = await fetch(`${BASE}/git/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // Confirmed Mappings (Review Queue)
  async listMappings(): Promise<{ mappings: MappingSummary[] }> {
    const res = await fetch(`${BASE}/mappings`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async getMapping(id: string): Promise<any> {
    const res = await fetch(`${BASE}/mappings/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async validateMappingTypes(mapping: any, entityType: string): Promise<{
    success: boolean; entity_type: string; fields: Record<string, {
      api_path: string; raw_value: any; expected_type: string;
      valid: boolean; error: string; suggestion: string;
    }>; all_valid: boolean;
  }> {
    const res = await fetch(`${BASE}/mapping/validate-types`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mapping, cmsd_entity: entityType }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  async deleteMapping(id: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${BASE}/mappings/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // Dependency inference for mapping authoring
  async inferDependencies(cmsdEntity: string, fieldMap: Record<string, any>): Promise<{
    entity: string;
    dependencies: string[];
    is_independent: boolean;
    independent_entities: string[];
    all_entities: string[];
  }> {
    const res = await fetch(`${BASE}/mapping/infer-dependencies`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cmsd_entity: cmsdEntity, mapping: fieldMap }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async createManualMapping(entityType: string, entries: Array<Record<string, any>>, dataPoint?: string) {
    const res = await fetch(`${BASE}/mappings/manual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entity_type: entityType, entries, data_point: dataPoint }),
    });
    if (!res.ok) throw new Error(`Manual mapping failed: ${res.status}`);
    return res.json();
  },
};