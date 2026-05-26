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
  status_code: number | null;
  size_bytes: number;
  raw_payload: any;
}

export interface FetchEndpointsResponse {
  success: boolean;
  payloads: FetchedPayload[];
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
  // Smart Reanalyze
  async smartReanalyze(body: SmartReanalyzeRequest) {
    const res = await fetch(`${BASE}/mapping/smart-reanalyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  // Mapping Queue (batch)
  async confirmMapping(id: string, body: any): Promise<{ success: boolean; saved_to: string; queue_size: number; message: string }> {
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
};