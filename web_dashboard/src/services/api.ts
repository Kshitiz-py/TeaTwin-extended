const BASE = '/api/cmsd/v1';

export interface ConnectionMetadata {
  mapping_id: string;
  source_url: string;
  key_field: string;
  key_value: string | null;
  last_fetched: string;
}

export interface RefreshReport {
  success: boolean;
  refreshed_at: string;
  phases: {
    preflight: { passed: boolean; warnings: any[] };
    topological_order: string[];
    generation: Record<string, { count: number; source: string }>;
    merge: { hardcoded_fallback: string[] };
  };
  fetch_errors: Array<{ entity_type: string; mapping_id?: string; endpoint: string; error: string }>;
  field_warnings: Array<{ entity_type: string; instance_key: string; field: string; api_path: string }>;
  changes_detected: number;
  elapsed_ms: number;
}

export interface RelationDefinition {
  cmsd_path: string;
  target_entity: string;
  target_mapping_id?: string;
  match_key: {
    source: { api_path: string; transform?: any };
    target: { field: string };
  };
  confidence?: string;
}

export interface PreflightRelationIssue {
  for_mapping: string;
  for_entity: string;
  relation_path: string;
  target_mapping_id: string;
  target_entity: string;
  resolved: boolean;
}

export interface PreflightResult {
  passed: boolean;
  checks: {
    dependencies: { passed: boolean; auto_selected: string[]; missing: any[] };
    relations: { passed: boolean; missing_targets: PreflightRelationIssue[] };
    field_coverage: { passed: boolean; unapproved: any[] };
    api_reachability: { passed: boolean; unreachable: any[] };
  };
}

export interface RefreshStatus {
  is_polling: boolean;
  poll_interval_seconds: number;
  last_refreshed: string | null;
  mappings_loaded: number;
}

export const api = {
  async getSummary() {
    const res = await fetch(`${BASE}/digital-twin/summary`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getResources() {
    const res = await fetch(`${BASE}/digital-twin/resources`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getOrders() {
    const res = await fetch(`${BASE}/digital-twin/orders`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getLayout() {
    const res = await fetch(`${BASE}/digital-twin/layout`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getChanges(limit = 50) {
    const res = await fetch(`${BASE}/changes?limit=${limit}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  // Refresh (Mapping-Driven Instance Generation)
  async refreshInstances(mappingIds?: string[], useHardcoded = true): Promise<RefreshReport> {
    const res = await fetch(`${BASE}/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mapping_ids: mappingIds, use_hardcoded: useHardcoded }),
    });
    if (!res.ok) throw new Error(`Refresh failed: ${res.status}`);
    return res.json();
  },

  async validatePreflight(mappingIds: string[]): Promise<PreflightResult> {
    const res = await fetch(`${BASE}/refresh/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mapping_ids: mappingIds }),
    });
    if (!res.ok) throw new Error(`Pre-flight failed: ${res.status}`);
    return res.json();
  },

  async getRefreshStatus(): Promise<RefreshStatus> {
    const res = await fetch(`${BASE}/refresh/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async setPolling(intervalSeconds: number): Promise<{ success: boolean; is_polling: boolean }> {
    const res = await fetch(`${BASE}/refresh/polling`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ interval_seconds: intervalSeconds }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
};