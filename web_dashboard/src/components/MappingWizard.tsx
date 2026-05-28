import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import EndpointRow, { EndpointRowData, PayloadStatus } from './EndpointRow';
import PayloadViewer from './PayloadViewer';
import MappingTable from './MappingTable';
import EntityPreview from './EntityPreview';
import MappingChat from './MappingChat';
import { agentApi, FetchedPayload } from '../services/agentApi';
import { SourceData } from './SourceCard';

function defaultEndpoint(sources: SourceData[]): EndpointRowData {
  return { source_id: sources[0]?.id || '', endpoint: '/resources', method: 'GET', label: '' };
}

type Phase = 'fetch' | 'analyzing' | 'map';

/** Parse a JSONPath count_path like "$.resources[*]" → "resources" */
function parseCountPath(countPath: string): string[] {
  // "$.resources[*]" → ["resources"]
  // "$.d.results[*]" → ["d", "results"]
  return countPath
    .replace(/^\$\./, '')
    .replace(/\[[*]\]$/, '')
    .split('.')
    .filter(Boolean);
}

/** Follow a dot-notation path into an object */
function getByPath(obj: any, path: string): any {
  if (!obj || !path) return undefined;
  const parts = path.split('.');
  let cur = obj;
  for (const p of parts) {
    if (cur == null || typeof cur !== 'object') return undefined;
    cur = cur[p];
  }
  return cur;
}

/** Strip the array prefix from an absolute api_path so it resolves against a single instance. */
function makeRelativePath(apiPath: string, countPath: string): string {
  if (!countPath || !apiPath) return apiPath;

  // Strip $. prefix if present: "$.machines[*].resource_id" → "machines[*].resource_id"
  let cleanPath = apiPath.replace(/^\$\./, '');

  const pathParts = parseCountPath(countPath);
  const arrayPrefix = pathParts.join('.');
  if (!arrayPrefix) return cleanPath;

  // Try stripping known array prefix patterns
  const patterns = [
    arrayPrefix + '.',       // "machines."
    arrayPrefix + '[*].',    // "machines[*]."
    arrayPrefix + '[',       // "machines[..."
  ];
  for (const pat of patterns) {
    if (cleanPath.startsWith(pat)) {
      let rest = cleanPath.slice(pat.length);
      rest = rest.replace(/^(\d+|\[[*]\])\./, '');
      return rest || cleanPath;
    }
  }

  // Fallback: strip leading segments that look like array path parts.
  // e.g. "d.results.0.field" with arrayPrefix "d.results" → try "field"
  const segments = cleanPath.split('.');
  const clean = segments.filter(s => s !== '' && !/^\d+$/.test(s) && s !== '[*]');
  // Remove array prefix segments from the front
  const prefixSegs = arrayPrefix.split('.');
  let startIdx = 0;
  while (startIdx < prefixSegs.length && startIdx < clean.length && clean[startIdx] === prefixSegs[startIdx]) {
    startIdx++;
  }
  if (startIdx > 0 && startIdx < clean.length) {
    return clean.slice(startIdx).join('.');
  }

  return cleanPath;
}

/** Client-side transformation mirroring backend execute_transformation.
 *  Re-applies user transforms during instance navigation without API calls. */
function applySimpleTransform(rawValue: string, transformation: any): string {
  if (!transformation || transformation.type === 'none') return rawValue;
  const params = transformation.params || {};
  try {
    switch (transformation.type) {
      case 'unit_conversion':
        return String(Number(rawValue) * Number(params.factor || 1));
      case 'enum_map': {
        const mapping = typeof params.mapping === 'string' ? JSON.parse(params.mapping) : (params.mapping || {});
        return String(mapping[rawValue] ?? rawValue);
      }
      case 'to_decimal': {
        const precision = parseInt(params.precision || '2', 10);
        return Number(rawValue).toFixed(precision);
      }
      case 'to_integer':
        return String(Math.round(Number(rawValue)));
      case 'string_template':
        return (params.template || '{value}').replace('{value}', rawValue);
      case 'divide_by': {
        const divisor = Number(params.divisor || 1);
        if (divisor === 0) return rawValue;
        return String(Number(rawValue) / divisor);
      }
      case 'multiply_by':
        return String(Number(rawValue) * Number(params.factor || 1));
      case 'default_value':
        return String(params.value ?? rawValue);
      default:
        return rawValue;
    }
  } catch {
    return rawValue;
  }
}

interface MappingWizardProps {
  onNavigateToQueue?: () => void;
  preloadedMapping?: any;  // full mapping JSON to edit (skips to Phase 2)
  onClearPreloaded?: () => void;  // called when user goes back to Phase 1
  devMode?: boolean;
}

export default function MappingWizard({ onNavigateToQueue, preloadedMapping, onClearPreloaded, devMode = false }: MappingWizardProps = {}) {
  const [sources, setSources] = useState<SourceData[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [endpoints, setEndpoints] = useState<EndpointRowData[]>([]);
  const [payloads, setPayloads] = useState<(FetchedPayload | null)[]>([]);
  const [loading, setLoading] = useState<Set<number>>(new Set());
  const [fireAllLoading, setFireAllLoading] = useState(false);

  const [approvedIndices, setApprovedIndices] = useState<Set<number>>(new Set());
  const [phase, setPhase] = useState<Phase>('fetch');
  const [dataPointName, setDataPointName] = useState('');
  const [cmsdEntity, setCmsdEntity] = useState('Resource');
  const [mappingResult, setMappingResult] = useState<any>(null);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  const [changedFields, setChangedFields] = useState<Set<string>>(new Set());
  const [editSaving, setEditSaving] = useState(false);
  const [endpointsExpanded, setEndpointsExpanded] = useState(false);
  const [previewExpanded, setPreviewExpanded] = useState(true);
  const [expandedPayload, setExpandedPayload] = useState<number | null>(null);

  // Review state
  const [fieldStatuses, setFieldStatuses] = useState<Record<string, 'approved' | 'flagged' | 'pending'>>({});
  const [fieldComments, setFieldComments] = useState<Record<string, string>>({});
  const [reanalyzeLoading, setReanalyzeLoading] = useState(false);

  // Smart reanalyze (user guidance)
  const [guidanceOpen, setGuidanceOpen] = useState(false);
  const [guidanceInput, setGuidanceInput] = useState('');
  const [guidanceLoading, setGuidanceLoading] = useState(false);

  // Confirm mapping
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [confirmPending, setConfirmPending] = useState(false);  // two-step: show Edit / Save & Continue
  const [mappingConfirmed, setMappingConfirmed] = useState(false);
  const [mappingConfirmId, setMappingConfirmId] = useState<string | null>(null);
  const [confirmResult, setConfirmResult] = useState<{
    cmsd_entity: string;
    field_count: number;
  } | null>(null);
  const [showConfirmToast, setShowConfirmToast] = useState(false);

  // Refs for preloaded data (avoids state batching issues)
  const preloadedPayloadsRef = useRef<FetchedPayload[]>([]);
  const preloadedEndpointsRef = useRef<EndpointRowData[]>([]);

  // Analyze progress
  const [analyzeSteps, setAnalyzeSteps] = useState<{ label: string; detail: string; status: 'pending' | 'running' | 'done' }[]>([]);
  const [analyzeProgress, setAnalyzeProgress] = useState(0);

  // Entity recommendation tiers
  const [existingEntities, setExistingEntities] = useState<Set<string>>(new Set());
  const [inferredDeps, setInferredDeps] = useState<string[]>([]);
  const [indepEntities, setIndepEntities] = useState<Set<string>>(new Set(CMSD_ENTITIES));

  // Fetch existing confirmed mapping entity types for tier computation
  useEffect(() => {
    agentApi.listMappings().then(data => {
      const entSet = new Set<string>();
      for (const m of data.mappings) {
        if (m.cmsd_entity) entSet.add(m.cmsd_entity);
      }
      setExistingEntities(entSet);
    }).catch(() => {});
  }, [phase]);

  // Type validation results
  const [typeValidation, setTypeValidation] = useState<any>(null);
  const runTypeValidation = useCallback(async (mapping: any, entity: string) => {
    try {
      const result = await agentApi.validateMappingTypes(mapping, entity);
      setTypeValidation(result.fields);
    } catch { setTypeValidation(null); }
  }, []);

  // Developer mode passed from App (global toggle in dashboard header)

  // Mapping chat
  const [chatOpen, setChatOpen] = useState(false);

  // Instance navigation
  const [currentInstanceIndex, setCurrentInstanceIndex] = useState(0);

  // Per-instance review state: keys are "${instanceIndex}:${fieldName}"
  const instanceKey = (field: string) => `${currentInstanceIndex}:${field}`;

  // Derived: fieldStatuses filtered to current instance, keyed by field name only
  const currentFieldStatuses = useMemo(() => {
    const prefix = `${currentInstanceIndex}:`;
    const result: Record<string, 'approved' | 'flagged' | 'pending'> = {};
    for (const [key, status] of Object.entries(fieldStatuses)) {
      if (key.startsWith(prefix)) {
        result[key.slice(prefix.length)] = status;
      }
    }
    return result;
  }, [fieldStatuses, currentInstanceIndex]);

  const currentFieldComments = useMemo(() => {
    const prefix = `${currentInstanceIndex}:`;
    const result: Record<string, string> = {};
    for (const [key, comment] of Object.entries(fieldComments)) {
      if (key.startsWith(prefix)) {
        result[key.slice(prefix.length)] = comment;
      }
    }
    return result;
  }, [fieldComments, currentInstanceIndex]);

  // Preload a saved mapping for editing (skip to Phase 2)
  useEffect(() => {
    if (!preloadedMapping) {
      // Clear refs when not editing — prevents stale data from previous edit sessions
      preloadedPayloadsRef.current = [];
      preloadedEndpointsRef.current = [];
      return;
    }
    const m = preloadedMapping;
    setDataPointName(m.data_point || m.data_point_name || '');
    setCmsdEntity(m.cmsd_entity || 'Resource');
    setMappingResult({ mapping: m });
    setPhase('map');
    setEndpointsExpanded(true);
    setPreviewExpanded(true);
    setMappingConfirmed(false);
    setConfirmPending(false);
    setShowConfirmToast(false);
    setConfirmResult(null);
    setCurrentInstanceIndex(0);

    // Store preloaded payloads/endpoints in refs (immediate, no render needed)
    const savedEndpoints = m.endpoints || [];
    preloadedPayloadsRef.current = savedEndpoints.map((ep: any) => ({
      endpoint: ep.endpoint || '',
      source_id: ep.source_id || '',
      label: ep.label || ep.endpoint || '',
      url: '',
      status: 'success' as const,
      status_code: 200,
      size_bytes: JSON.stringify(ep.raw_payload || {}).length,
      raw_payload: ep.raw_payload || null,
    }));
    preloadedEndpointsRef.current = savedEndpoints.map((ep: any) => ({
      source_id: ep.source_id || '',
      endpoint: ep.endpoint || '',
      method: 'GET' as const,
      label: ep.label || ep.endpoint || '',
    }));

    // Restore field statuses
    const fieldMap = m.mapping || {};
    const newStatuses: Record<string, 'approved' | 'flagged' | 'pending'> = {};
    if (m.instances?.count_path && m.instances?.key_field && savedEndpoints.length > 0) {
      const countPath = m.instances.count_path;
      const pathParts = countPath.replace('$.', '').replace('[*]', '').split('.').filter(Boolean);
      for (const ep of savedEndpoints) {
        if (!ep.raw_payload) continue;
        let arr: any = ep.raw_payload;
        for (const p of pathParts) {
          if (arr && typeof arr === 'object' && p in arr) arr = arr[p];
          else { arr = null; break; }
        }
        if (Array.isArray(arr) && arr.length > 0) {
          for (let i = 0; i < arr.length; i++) {
            for (const fieldName of Object.keys(fieldMap)) {
              if (typeof fieldMap[fieldName] === 'object') {
                newStatuses[`${i}:${fieldName}`] = 'approved';
              }
            }
          }
          break;
        }
      }
    }
    if (Object.keys(newStatuses).length > 0) {
      setFieldStatuses(prev => ({ ...prev, ...newStatuses }));
    }
  }, [preloadedMapping]);

  // Run type validation whenever mapping or entity changes
  useEffect(() => {
    if (mappingResult?.mapping && phase === 'map') {
      runTypeValidation(mappingResult.mapping, cmsdEntity);
    }
  }, [mappingResult, cmsdEntity, phase, runTypeValidation]);

  // Infer dependencies for current entity (authoring-time hint + Phase 2 display)
  useEffect(() => {
    agentApi.inferDependencies(cmsdEntity, {}).then(info => {
      setInferredDeps(info.dependencies);
      setIndepEntities(new Set(info.independent_entities));
    }).catch(() => {});
  }, [cmsdEntity]);

  useEffect(() => {
    agentApi.getSources()
      .then(data => {
        const srcs = data.sources || [];
        setSources(srcs);
        if (srcs.length > 0) {
          setEndpoints([defaultEndpoint(srcs)]);
          setPayloads([null]);
        }
      })
      .catch(() => setSourceError('Failed to load data sources.'))
      .finally(() => setSourcesLoading(false));
  }, []);

  const addEndpoint = () => {
    setEndpoints(prev => [...prev, defaultEndpoint(sources)]);
    setPayloads(prev => [...prev, null]);
  };

  const removeEndpoint = (i: number) => {
    if (endpoints.length <= 1) return;
    setEndpoints(prev => prev.filter((_, idx) => idx !== i));
    setPayloads(prev => prev.filter((_, idx) => idx !== i));
    setApprovedIndices(prev => {
      const next = new Set(prev); next.delete(i);
      const adjusted = new Set<number>();
      next.forEach(idx => adjusted.add(idx > i ? idx - 1 : idx));
      return adjusted;
    });
  };

  const updateEndpoint = (i: number, data: EndpointRowData) => {
    setEndpoints(prev => prev.map((ep, idx) => idx === i ? data : ep));
  };

  const fireSingle = async (i: number) => {
    const ep = endpoints[i];
    if (!ep) return;
    setLoading(prev => new Set(prev).add(i));
    try {
      const result = await agentApi.fetchEndpoints([{
        source_id: ep.source_id, endpoint: ep.endpoint,
        method: ep.method, label: ep.label || ep.endpoint,
      }]);
      setPayloads(prev => prev.map((p, idx) => idx === i ? result.payloads[0] : p));
      setApprovedIndices(prev => { const next = new Set(prev); next.delete(i); return next; });
    } catch (e: any) {
      setPayloads(prev => prev.map((p, idx) => idx === i ? {
        endpoint: ep.endpoint, source_id: ep.source_id, label: ep.label || ep.endpoint,
        url: '', status: 'error' as const, error_message: e.message || 'Fetch failed',
        status_code: null, size_bytes: 0, raw_payload: null,
      } : p));
      setApprovedIndices(prev => { const next = new Set(prev); next.delete(i); return next; });
    } finally {
      setLoading(prev => { const next = new Set(prev); next.delete(i); return next; });
    }
  };

  const fireAll = async () => {
    setFireAllLoading(true);
    try {
      const result = await agentApi.fetchEndpoints(
        endpoints.map(ep => ({ source_id: ep.source_id, endpoint: ep.endpoint, method: ep.method, label: ep.label || ep.endpoint }))
      );
      setPayloads(result.payloads);
      setApprovedIndices(new Set());
    } catch (e: any) {
      setPayloads(endpoints.map(ep => ({
        endpoint: ep.endpoint, source_id: ep.source_id, label: ep.label || ep.endpoint,
        url: '', status: 'error' as const, error_message: e.message || 'Fire All failed',
        status_code: null, size_bytes: 0, raw_payload: null,
      })));
      setApprovedIndices(new Set());
    } finally { setFireAllLoading(false); }
  };

  const toggleApprove = (i: number) => {
    setApprovedIndices(prev => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i); else next.add(i);
      return next;
    });
  };

  const buildApprovedPayloads = useCallback(() => {
    return Array.from(approvedIndices).map(i => {
      const ep = endpoints[i]; const pl = payloads[i];
      return { endpoint: ep.endpoint, source_id: ep.source_id, label: ep.label || ep.endpoint, raw_payload: pl?.raw_payload ?? null };
    });
  }, [approvedIndices, endpoints, payloads]);

  const approveAndMap = () => {
    const approvedPayloads = buildApprovedPayloads();
    setPhase('analyzing'); setAnalyzeError(null);
    setCurrentInstanceIndex(0);
    setFieldStatuses({}); setFieldComments({});
    setAnalyzeProgress(5);

    // Initialize with first step running
    const stepMap: Record<string, { label: string; detail: string }> = {
      payloads: { label: 'Parsing API payloads...', detail: `${approvedPayloads.length} payload(s) to analyze` },
      rag: { label: 'Retrieving RAG context...', detail: 'Searching CMSD knowledge base' },
      llm: { label: 'Analyzing with LLM...', detail: `Mapping to ${cmsdEntity}` },
    };

    setAnalyzeSteps([
      { ...stepMap.payloads, status: 'running' as const },
      { ...stepMap.rag, status: 'pending' as const },
      { ...stepMap.llm, status: 'pending' as const },
    ]);

    const pctByPhase: Record<string, number> = { payloads: 15, rag: 35, llm: 85 };

    agentApi.analyzeMappingStream(
      { data_point_name: dataPointName || 'Untitled Data Point', cmsd_entity: cmsdEntity, approved_payloads: approvedPayloads },
      (step) => {
        const { phase, status: s, detail } = step;
        const phaseLabel = stepMap[phase]?.label;
        if (s === 'running') {
          setAnalyzeSteps(prev => prev.map(st => ({
            ...st,
            status: (st.label === phaseLabel ? 'running' : st.status) as 'pending' | 'running' | 'done',
          })));
          setAnalyzeProgress(pctByPhase[phase] || 50);
        } else if (s === 'done') {
          setAnalyzeSteps(prev => prev.map(st => ({
            ...st,
            status: (st.label === phaseLabel ? 'done' : st.status) as 'pending' | 'running' | 'done',
            detail: (st.label === phaseLabel && detail) ? detail : st.detail,
          })));
          setAnalyzeProgress(pctByPhase[phase] || 50);
        }
      },
      (result) => {
        // Final result
        const fieldCount = Object.keys(result.mapping?.mapping || {}).length;
        setAnalyzeSteps(prev => prev.map(s => ({ ...s, status: 'done' as const })));
        setAnalyzeProgress(100);
        setTimeout(() => {
          setMappingResult(result);
          setPhase('map');
        }, 500);
      },
      (error) => {
        setAnalyzeError(error); setPhase('fetch');
      },
    );
  };

  const handleMappingChange = async (updatedMapping: any) => {
    // Merge edited fields into saved state — preserve original raw_value/converted_value
    // for untouched fields so instance-specific live data isn't baked into the saved mapping.
    setMappingResult((prev: any) => {
      const prevMapping = prev?.mapping || {};
      const prevFields = prevMapping?.mapping || {};
      const incomingFields = updatedMapping?.mapping || {};
      const mergedFields: Record<string, any> = { ...prevFields };
      for (const [key, value] of Object.entries(incomingFields)) {
        const f = value as Record<string, any>;
        if (f && f.confidence === 'manual') {
          mergedFields[key] = f; // user edit — take the new version
        } else if (!mergedFields[key]) {
          mergedFields[key] = f; // new field from LLM
        }
      }
      return {
        ...prev,
        mapping: {
          ...prevMapping,
          ...updatedMapping,
          mapping: mergedFields,
        },
      };
    });
    const newFields = updatedMapping?.mapping ?? {};
    const changed = new Set<string>();
    for (const key of Object.keys(newFields)) {
      if (newFields[key]?.confidence === 'manual') changed.add(key);
    }
    setChangedFields(changed);
    setEditSaving(true);
    try {
      const edits: Record<string, any> = {};
      for (const key of Object.keys(newFields)) {
        if (newFields[key]?.confidence === 'manual') edits[key] = newFields[key];
      }
      if (Object.keys(edits).length > 0) {
        await agentApi.editMapping({ current_mapping: mappingResult?.mapping || {}, edits });
      }
    } catch { /* edits preserved locally */ }
    finally { setEditSaving(false); }
  };

  const handleAddMapping = (fieldName: string) => {
    if (!mappingResult?.mapping) return;
    const currentMapping = { ...mappingResult.mapping };
    const fields = { ...(currentMapping.mapping || {}) };
    fields[fieldName] = { api_path: '', type_conversion: 'none', raw_value: '', converted_value: '', sample_value: '', confidence: 'manual', source_endpoint: '', transformation: null };
    currentMapping.mapping = fields;
    currentMapping.unmapped_fields = (currentMapping.unmapped_fields || []).filter((f: string) => f !== fieldName);
    currentMapping.requires_manual_review = (currentMapping.unmapped_fields || []).length > 0;
    setMappingResult((prev: any) => ({ ...prev, mapping: currentMapping }));
    setChangedFields(new Set([fieldName]));
    agentApi.editMapping({ current_mapping: mappingResult.mapping, edits: { [fieldName]: fields[fieldName] } }).catch(() => {});
  };

  // ── Review handlers ────────────────────────────────────────

  const handleStatusChange = (field: string, status: 'approved' | 'flagged' | 'pending') => {
    const key = instanceKey(field);
    setFieldStatuses(prev => ({ ...prev, [key]: status }));
  };

  const handleCommentChange = (field: string, comment: string) => {
    const key = instanceKey(field);
    setFieldComments(prev => ({ ...prev, [key]: comment }));
  };

  const handleReviewReanalyze = async () => {
    // Collect flagged fields from ALL instances (keys are "${instanceIndex}:${fieldName}")
    const flaggedEntries = Object.entries(fieldStatuses)
      .filter(([, s]) => s === 'flagged');

    if (flaggedEntries.length === 0) return;

    // Deduplicate by field name, collecting comments
    const fieldCommentMap = new Map<string, string>();
    for (const [key, ] of flaggedEntries) {
      // Extract field name from "${instanceIndex}:${fieldName}"
      const lastColon = key.lastIndexOf(':');
      const fieldName = lastColon >= 0 ? key.slice(lastColon + 1) : key;
      const comment = fieldComments[key] || '';
      if (!fieldCommentMap.has(fieldName) || comment) {
        fieldCommentMap.set(fieldName, comment);
      }
    }
    const flaggedFields = Array.from(fieldCommentMap.entries()).map(([field, comment]) => ({ field, comment }));

    const approvedPayloads = buildApprovedPayloads();
    setReanalyzeLoading(true);
    try {
      const result = await agentApi.reviewReanalyze({
        current_mapping: mappingResult?.mapping || {},
        flagged_fields: flaggedFields,
        data_point_name: dataPointName || 'Untitled Data Point',
        cmsd_entity: analyzedEntity || cmsdEntity,
        approved_payloads: approvedPayloads,
      });
      setMappingResult((prev: any) => ({
        ...prev,
        mapping: result.refined_mapping,
      }));
      // Reset flagged fields to pending on ALL instances
      setFieldStatuses(prev => {
        const next = { ...prev };
        for (const [key, status] of Object.entries(prev)) {
          if (status === 'flagged') next[key] = 'pending';
        }
        return next;
      });
      setFieldComments({});
      setChangedFields(new Set(flaggedFields.map(f => f.field)));
    } catch (e: any) {
      // Keep flagged state on error so user can retry
    } finally {
      setReanalyzeLoading(false);
    }
  };

  const handleSmartReanalyze = async () => {
    const guidance = guidanceInput.trim();
    if (!guidance || !mappingResult?.mapping) return;

    // Only send fields NOT approved on the CURRENT instance to prevent LLM from changing them
    const fullMapping = mappingResult.mapping;
    const fields = { ...(fullMapping.mapping || {}) };
    const unlockedFields: Record<string, any> = {};
    for (const [fieldName, value] of Object.entries(fields)) {
      const status = currentFieldStatuses[fieldName] || 'pending';
      if (status !== 'approved') {
        unlockedFields[fieldName] = value;
      }
    }

    // Augment guidance with per-field comments from flagged fields on ALL instances
    const flaggedComments: string[] = [];
    for (const [key, status] of Object.entries(fieldStatuses)) {
      if (status === 'flagged') {
        const lastColon = key.lastIndexOf(':');
        const fieldName = lastColon >= 0 ? key.slice(lastColon + 1) : key;
        const comment = fieldComments[key];
        if (comment) {
          flaggedComments.push(`  - ${fieldName}: ${comment}`);
        }
      }
    }
    let fullGuidance = guidance;
    if (flaggedComments.length > 0) {
      fullGuidance = `${guidance}\n\nUser comments on flagged fields (prioritize fixing these):\n${flaggedComments.join('\n')}`;
    }

    const approvedPayloads = buildApprovedPayloads();
    setGuidanceLoading(true);
    try {
      const result = await agentApi.smartReanalyze({
        data_point_name: dataPointName || 'Untitled Data Point',
        cmsd_entity: analyzedEntity || cmsdEntity,
        current_mapping: { ...fullMapping, mapping: unlockedFields },
        user_guidance: fullGuidance,
      });
      // Merge: preserve fields approved on current instance, take LLM changes for others
      const mergedFields = { ...fields };
      const refinedFields = result.proposed_mapping?.mapping || result.refined_mapping?.mapping || {};
      for (const [fieldName, value] of Object.entries(refinedFields)) {
        const status = currentFieldStatuses[fieldName] || 'pending';
        if (status !== 'approved') {
          mergedFields[fieldName] = value;
        }
      }
      setMappingResult((prev: any) => ({
        ...prev,
        mapping: { ...fullMapping, mapping: mergedFields },
      }));
      setGuidanceOpen(false);
      setGuidanceInput('');
    } catch (e: any) {
      // Keep guidance open on error so user can retry
    } finally {
      setGuidanceLoading(false);
    }
  };

  const handleConfirmMapping = () => {
    if (!mappingResult?.mapping) return;
    // Step 1: show Edit / Save & Continue
    setConfirmPending(true);
  };

  const handleSaveAndContinue = async () => {
    if (!mappingResult?.mapping) return;
    setConfirmLoading(true);
    setConfirmPending(false);
    try {
      // Sync current name into mapping before saving
      if (dataPointName) {
        mappingResult.mapping.data_point = dataPointName;
      }
      const id = `${(dataPointName || 'mapping').replace(/\s+/g, '-').toLowerCase()}-${Date.now()}`;
      const approvedPayloads = approvedPayloadEntries
        .filter(e => e.payload?.status === 'success' && e.payload?.raw_payload)
        .map(e => ({
          endpoint: e.payload!.endpoint,
          source_id: e.payload!.source_id,
          label: e.payload!.label || e.payload!.endpoint,
          raw_payload: e.payload!.raw_payload,
        }));
      const result = await agentApi.confirmMapping(id, {
        mapping: mappingResult.mapping,
        approved_payloads: approvedPayloads,
      });
      setMappingConfirmed(true);
      setMappingConfirmId(id);
      setConfirmResult({
        cmsd_entity: result.cmsd_entity,
        field_count: result.field_count,
      });
      setShowConfirmToast(true);
    } catch {
      // Mapping remains editable
    } finally {
      setConfirmLoading(false);
    }
  };

  const handleEditMapping = () => {
    // Cancel confirmation — go back to editing
    setConfirmPending(false);
  };

  const handleApproveAllFields = () => {
    const fields = mappingResult?.mapping?.mapping ?? {};
    const fieldNames = Object.keys(fields);
    if (fieldNames.length === 0) return;
    // Toggle: if all are already approved for THIS instance, revert to pending
    const allApproved = fieldNames.every(f => (currentFieldStatuses[f] || 'pending') === 'approved');
    const newStatuses: Record<string, 'approved' | 'pending'> = {};
    for (const fieldName of fieldNames) {
      newStatuses[instanceKey(fieldName)] = allApproved ? 'pending' : 'approved';
    }
    setFieldStatuses(prev => ({ ...prev, ...newStatuses }));
  };

  const handleApproveAllInstances = () => {
    const fields = mappingResult?.mapping?.mapping ?? {};
    const fieldNames = Object.keys(fields);
    if (fieldNames.length === 0 || !instanceInfo || instanceInfo.count === 0) return;
    // Toggle: if ALL instances have ALL fields approved, revert; otherwise approve all
    const allApproved = allFieldsAllInstancesApproved;
    const newStatuses: Record<string, 'approved' | 'pending'> = {};
    for (let i = 0; i < instanceInfo.count; i++) {
      for (const fieldName of fieldNames) {
        newStatuses[`${i}:${fieldName}`] = allApproved ? 'pending' : 'approved';
      }
    }
    setFieldStatuses(prev => ({ ...prev, ...newStatuses }));
  };

  const handleChatSend = async (msg: string): Promise<string> => {
    const result = await agentApi.chatMapping({
      data_point_name: dataPointName || 'Untitled Data Point',
      current_mapping: mappingResult?.mapping || {},
      user_question: msg,
    });
    return result.response || 'No response';
  };

  const getPayloadStatus = (i: number): PayloadStatus => {
    const pl = payloads[i]; if (!pl) return 'none';
    return pl.status === 'success' ? 'success' : 'error';
  };

  // ── Derived state ──────────────────────────────────────────

  const isLoadingAny = loading.size > 0 || fireAllLoading;
  const approvedCount = approvedIndices.size;
  const canApprove = approvedCount > 0 && !isLoadingAny;
  const availableEndpoints = endpoints.filter((_, i) => approvedIndices.has(i)).map(ep => ep.label || ep.endpoint);
  const fields = mappingResult?.mapping?.mapping ?? {};
  const mappedFieldCount = Object.keys(fields).length;
  const analyzedEntity = mappingResult?.mapping?.cmsd_entity || mappingResult?.cmsd_entity || '';
  const unmappedCount = mappingResult?.mapping?.unmapped_fields?.length || 0;

  const approvedPayloadEntries = (() => {
    // Use preloaded refs if available (editing from Review Queue)
    if (preloadedPayloadsRef.current.length > 0) {
      return preloadedPayloadsRef.current.map((pl, i) => ({
        label: preloadedEndpointsRef.current[i]?.label || pl.label || pl.endpoint || '',
        endpoint: preloadedEndpointsRef.current[i]?.endpoint || pl.endpoint || '',
        payload: pl,
        index: i,
      }));
    }
    return Array.from(approvedIndices).map(i => ({
      label: endpoints[i]?.label || endpoints[i]?.endpoint || '',
      endpoint: endpoints[i]?.endpoint || '',
      payload: payloads[i],
      index: i,
    }));
  })();

  // ── Extract instances from approved payloads ───────────────

  const instanceInfo = useMemo(() => {
    const countPath = mappingResult?.mapping?.instances?.count_path;
    const keyField = mappingResult?.mapping?.instances?.key_field;
    if (!countPath || !keyField || phase !== 'map') return null;

    const pathParts = parseCountPath(countPath);

    // Use preloaded refs if available (editing from Review Queue)
    const sources = preloadedPayloadsRef.current.length > 0
      ? preloadedPayloadsRef.current
      : approvedIndices.size > 0
        ? Array.from(approvedIndices).map(i => payloads[i]).filter(Boolean)
        : [];

    for (const pl of sources) {
      if (!pl || pl.status !== 'success' || !pl.raw_payload) continue;

      let current: any = pl.raw_payload;

      for (const part of pathParts) {
        if (current && typeof current === 'object' && part in current) {
          current = current[part];
        } else {
          current = null;
          break;
        }
      }

      if (Array.isArray(current) && current.length > 0) {
        const identifiers = current.map((item: any, i: number) => {
          const id = getByPath(item, keyField);
          return id != null ? String(id) : `[${i}]`;
        });
        return { identifiers, instances: current, count: current.length };
      }
    }

    return null;
  }, [mappingResult, approvedIndices, payloads, phase]);

  const currentInstanceData = useMemo(() => {
    if (!instanceInfo || instanceInfo.count === 0) return undefined;
    const idx = Math.min(currentInstanceIndex, instanceInfo.count - 1);
    return instanceInfo.instances[idx] || undefined;
  }, [instanceInfo, currentInstanceIndex]);

  // Overlay current instance values onto the mapping for live table display
  const liveMapping = useMemo(() => {
    if (!mappingResult?.mapping) return mappingResult?.mapping ?? null;
    const engineResult = { ...mappingResult.mapping };
    const fields = { ...(engineResult.mapping || {}) };
    let changed = false;

    for (const [cmsdField, info] of Object.entries(fields)) {
      if (!info || typeof info !== 'object') continue;
      const fieldInfo = info as Record<string, any>;
      const apiPath = fieldInfo.api_path;
      if (!apiPath || !currentInstanceData) continue;

      let actual = getByPath(currentInstanceData, apiPath);
      // If not found, try stripping the array prefix (LLM may use absolute paths)
      if (actual === undefined) {
        const countPath = mappingResult?.mapping?.instances?.count_path || '';
        const relative = makeRelativePath(apiPath, countPath);
        if (relative !== apiPath) {
          actual = getByPath(currentInstanceData, relative);
        }
      }
      if (actual !== undefined && actual !== null) {
        const displayVal = typeof actual === 'object' ? JSON.stringify(actual) : String(actual);
        // If user applied a transformation, re-apply it to the new raw value
        const newConverted = fieldInfo.transformation
          ? applySimpleTransform(displayVal, fieldInfo.transformation)
          : displayVal;
        if (fieldInfo.raw_value !== displayVal || fieldInfo.converted_value !== newConverted) {
          fields[cmsdField] = {
            ...fieldInfo,
            raw_value: displayVal,
            converted_value: newConverted,
          };
          changed = true;
        }
      }
    }

    // Always return a fresh mapping reference so the table renders
    // with the current instance's data (even if values match the LLM's original).
    return { ...engineResult, mapping: changed ? fields : { ...fields } };
  }, [mappingResult, currentInstanceData]);

  // NOTE: instance index is reset explicitly in approveAndMap().
  // Do NOT reset on every mappingResult change — that would boot the user
  // back to instance 0 on every table edit (transform dropdown, source change, etc.).

  // Keyboard: Ctrl+Left / Ctrl+Right for instance navigation
  useEffect(() => {
    if (phase !== 'map' || !instanceInfo || instanceInfo.count <= 1) return;
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (e.ctrlKey && e.key === 'ArrowLeft') {
        e.preventDefault();
        setCurrentInstanceIndex(prev => prev > 0 ? prev - 1 : instanceInfo.count - 1);
      } else if (e.ctrlKey && e.key === 'ArrowRight') {
        e.preventDefault();
        setCurrentInstanceIndex(prev => prev < instanceInfo.count - 1 ? prev + 1 : 0);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [phase, instanceInfo]);

  const hasInstances = instanceInfo && instanceInfo.count > 1;
  const currentIdentifier = instanceInfo
    ? instanceInfo.identifiers[Math.min(currentInstanceIndex, instanceInfo.count - 1)]
    : '';

  // True only when every field of every instance has been approved
  const allFieldsAllInstancesApproved = useMemo(() => {
    const fields = mappingResult?.mapping?.mapping ?? {};
    const fieldNames = Object.keys(fields);
    if (fieldNames.length === 0) return false;
    if (!instanceInfo || instanceInfo.count === 0) return false;
    for (let i = 0; i < instanceInfo.count; i++) {
      for (const fieldName of fieldNames) {
        if ((fieldStatuses[`${i}:${fieldName}`] || 'pending') !== 'approved') return false;
      }
    }
    return true;
  }, [fieldStatuses, mappingResult, instanceInfo]);

  // ── Render ──────────────────────────────────────────────────

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto' }}>
      <style>{'@keyframes spin { to { transform: rotate(360deg); } }'}</style>

      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ color: '#f1f5f9', margin: '0 0 4px', fontSize: '20px' }}>API Explorer</h2>
        <p style={{ color: '#94a3b8', margin: 0, fontSize: '13px' }}>
          Add endpoints, fire individually or all at once. Approve payloads to map them to CMSD entities.
        </p>
      </div>

      {sourceError && (
        <div style={{ padding: '10px 16px', background: '#7f1d1d', borderRadius: '8px', border: '1px solid #ef4444', color: '#fca5a5', fontSize: '13px', marginBottom: '14px' }}>
          {sourceError}
        </div>
      )}

      {sourcesLoading ? (
        <div style={{ padding: '24px', textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>Loading sources...</div>
      ) : sources.length === 0 ? (
        <div style={{ padding: '32px', textAlign: 'center', background: '#1e293b', borderRadius: '8px', border: '1px dashed #475569', color: '#94a3b8', fontSize: '13px' }}>
          No data sources configured. Use the <strong>Connect Sources</strong> step first.
        </div>
      ) : (
        <>
          {/* ═══════ PHASE 1: FETCH ═══════ */}
          {(phase === 'fetch' || phase === 'analyzing') && (
            <>
              {endpoints.length === 0 && (
                <div style={{ padding: '32px', textAlign: 'center', background: '#1e293b', borderRadius: '8px', border: '1px dashed #475569', color: '#94a3b8', fontSize: '13px', marginBottom: '12px' }}>
                  Add at least one endpoint to begin.
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {endpoints.map((ep, i) => (
                  <div key={i}>
                    <EndpointRow
                      data={ep} sources={sources}
                      onChange={(d) => updateEndpoint(i, d)}
                      onRemove={() => removeEndpoint(i)}
                      onFire={() => fireSingle(i)}
                      loading={loading.has(i)}
                      canRemove={endpoints.length > 1}
                      approved={approvedIndices.has(i)}
                      onApproveChange={() => toggleApprove(i)}
                      payloadStatus={getPayloadStatus(i)}
                    />
                    {payloads[i] && <PayloadViewer payload={payloads[i]} onRetry={() => fireSingle(i)} />}
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', gap: '10px', marginTop: '14px', paddingTop: '14px', borderTop: '1px solid #334155', alignItems: 'center' }}>
                <button onClick={addEndpoint} disabled={isLoadingAny} style={{ padding: '8px 18px', borderRadius: '6px', border: '1px dashed #475569', background: '#1e3a5f', color: isLoadingAny ? '#64748b' : '#93c5fd', cursor: isLoadingAny ? 'not-allowed' : 'pointer', fontSize: '13px', fontWeight: 600 }}>
                  + Add Endpoint
                </button>
                <button onClick={fireAll} disabled={endpoints.length === 0 || isLoadingAny} style={{ padding: '10px 28px', borderRadius: '6px', border: 'none', background: endpoints.length === 0 || isLoadingAny ? '#334155' : '#7c3aed', color: endpoints.length === 0 || isLoadingAny ? '#64748b' : '#fff', cursor: endpoints.length === 0 || isLoadingAny ? 'not-allowed' : 'pointer', fontSize: '14px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {fireAllLoading ? <>⏳ Fetching {endpoints.length} endpoint{endpoints.length !== 1 ? 's' : ''}...</> : <>🚀 Fire All ({endpoints.length})</>}
                </button>
              </div>

              {/* ═══ Entity Selection Step ═══ */}
              <div style={{ marginTop: '20px', paddingTop: '18px', borderTop: '2px solid #475569' }}>
                <label style={{ ...labelStyle, marginBottom: '8px' }}>What do you want to map?</label>

                {/* Recommendation tiers */}
                <EntityTierPicker
                  cmsdEntity={cmsdEntity}
                  onSelect={setCmsdEntity}
                  existingEntities={existingEntities}
                />

                {/* Direct select fallback */}
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                  <div style={{ minWidth: '180px' }}>
                    <label style={labelStyle}>Data Point Name</label>
                    <input value={dataPointName} onChange={e => setDataPointName(e.target.value)} placeholder="e.g. Factory Resources" style={inputStyle} />
                  </div>
                  <div style={{ minWidth: '160px' }}>
                    <label style={labelStyle}>CMSD Entity</label>
                    <select value={cmsdEntity} onChange={e => setCmsdEntity(e.target.value)} style={selectStyle}>
                      {CMSD_ENTITIES.map(e => <option key={e} value={e}>{e}</option>)}
                    </select>
                  </div>
                  <button onClick={approveAndMap} disabled={!canApprove} style={{ padding: '10px 28px', borderRadius: '6px', border: 'none', background: canApprove ? '#22c55e' : '#334155', color: canApprove ? '#fff' : '#64748b', cursor: canApprove ? 'pointer' : 'not-allowed', fontSize: '14px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px', whiteSpace: 'nowrap', height: '42px' }}>
                    {approvedCount > 0 ? `Approve ${approvedCount} Selected & Map` : 'Approve Selected & Map'}
                  </button>
                </div>
              </div>
            </>
          )}

          {/* ═══════ ANALYZING ═══════ */}
          {phase === 'analyzing' && (
            <div style={{
              position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
              background: 'rgba(15,23,42,0.85)', display: 'flex',
              alignItems: 'center', justifyContent: 'center', zIndex: 2000,
            }}>
              <div style={{
                background: '#1e293b', borderRadius: '12px', border: '1px solid #334155',
                padding: '32px 40px', width: '440px',
              }}>
                <p style={{ margin: '0 0 24px', color: '#f1f5f9', fontSize: '15px', fontWeight: 600 }}>
                  Analyzing with RAG + LLM
                </p>

                {/* Steps */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '20px' }}>
                  {analyzeSteps.map((s, i) => (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'center', gap: '10px',
                      padding: '7px 10px', borderRadius: '6px',
                      background: s.status === 'running' ? '#1e3a5f' : 'transparent',
                    }}>
                      <span style={{
                        width: '20px', height: '20px', borderRadius: '50%',
                        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                        flexShrink: 0, fontSize: '10px', fontWeight: 700,
                        background: s.status === 'done' ? '#064e3b' : '#1e3a5f',
                        border: `1.5px solid ${s.status === 'done' ? '#22c55e' : '#3b82f6'}`,
                        color: s.status === 'done' ? '#6ee7b7' : '#93c5fd',
                      }}>
                        {s.status === 'done' ? '✓' : (
                          <span style={{ display: 'inline-block', width: '8px', height: '8px', border: '2px solid #3b82f6', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.6s linear infinite' }} />
                        )}
                      </span>
                      <div style={{ flex: 1 }}>
                        <div style={{ color: '#e2e8f0', fontSize: '13px', fontWeight: 500 }}>{s.label}</div>
                        <div style={{ color: '#64748b', fontSize: '11px', marginTop: '1px' }}>{s.detail}</div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Progress bar — indeterminate while waiting, fills on complete */}
                <div style={{ height: '3px', background: '#334155', borderRadius: '2px', overflow: 'hidden' }}>
                  {analyzeProgress < 100 ? (
                    <div style={{
                      height: '100%', width: '30%', background: '#818cf8', borderRadius: '2px',
                      animation: 'indeterminate 1.2s ease-in-out infinite',
                    }} />
                  ) : (
                    <div style={{
                      height: '100%', width: '100%', background: '#22c55e', borderRadius: '2px',
                      transition: 'width 0.4s ease',
                    }} />
                  )}
                </div>
                <style>{`
                  @keyframes indeterminate {
                    0% { transform: translateX(-100%); }
                    100% { transform: translateX(430%); }
                  }
                `}</style>
              </div>
            </div>
          )}

          {analyzeError && phase === 'fetch' && (
            <div style={{ marginTop: '12px', padding: '10px 16px', background: '#7f1d1d', borderRadius: '8px', border: '1px solid #ef4444', color: '#fca5a5', fontSize: '13px' }}>
              {analyzeError}
            </div>
          )}

          {/* ═══════ PHASE 2: MAP ═══════ */}
          {phase === 'map' && mappingResult && (
            <div style={{ marginTop: '4px' }}>
              {/* ── Confirm success toast ── */}
              {showConfirmToast && confirmResult && (
                <div style={{
                  padding: '12px 20px', background: '#14532d', borderRadius: '8px',
                  border: '1px solid #22c55e', display: 'flex', alignItems: 'center',
                  justifyContent: 'space-between', marginBottom: '16px',
                  position: 'sticky', top: '0', zIndex: 10,
                }}>
                  <div>
                    <span style={{ color: '#86efac', fontWeight: 700, fontSize: '14px' }}>
                      ✓ Mapping saved
                    </span>
                    <span style={{ color: '#94a3b8', fontSize: '13px', marginLeft: '12px' }}>
                      {confirmResult.cmsd_entity} — {confirmResult.field_count} fields
                    </span>
                  </div>
                  <button
                    onClick={() => onNavigateToQueue?.()}
                    style={{
                      padding: '6px 16px', borderRadius: '6px', border: '1px solid #22c55e',
                      background: 'transparent', color: '#86efac', cursor: 'pointer',
                      fontSize: '13px', fontWeight: 600,
                    }}
                  >
                    Go to Review Queue →
                  </button>
                </div>
              )}
              {/* ── Header bar ── */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px',
                padding: '10px 14px', background: '#1e293b', borderRadius: '8px',
                border: '1px solid #334155', flexWrap: 'wrap',
              }}>
                <button onClick={() => { setPhase('fetch'); setAnalyzeError(null); onClearPreloaded?.(); }}
                  style={{ padding: '5px 10px', borderRadius: '4px', border: '1px solid #334155', background: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: '12px', fontWeight: 500, whiteSpace: 'nowrap' }}>
                  &larr; Endpoints
                </button>

                <button onClick={() => setEndpointsExpanded(!endpointsExpanded)}
                  style={{ padding: '5px 10px', borderRadius: '4px', border: '1px solid #334155', background: endpointsExpanded ? '#1e3a5f' : 'transparent', color: endpointsExpanded ? '#93c5fd' : '#94a3b8', cursor: 'pointer', fontSize: '12px', fontWeight: 500 }}>
                  {endpointsExpanded ? '▾' : '▸'} {approvedPayloadEntries.length} endpoint{approvedPayloadEntries.length !== 1 ? 's' : ''}
                </button>

                <span style={{ color: '#334155', fontSize: '14px' }}>|</span>

                {/* Mapping name */}
                <input
                  value={dataPointName}
                  onChange={e => setDataPointName(e.target.value)}
                  placeholder="Untitled Data Point"
                  style={{
                    padding: '4px 8px', borderRadius: '4px', background: '#0f172a',
                    border: '1px solid #334155', color: '#f1f5f9', fontSize: '12px',
                    fontWeight: 600, fontFamily: 'monospace', width: '160px', outline: 'none',
                  }}
                />
                <span style={{ fontSize: '12px', color: '#475569', fontFamily: 'monospace', userSelect: 'none' }}>.json</span>

                {/* Entity (fixed from Phase 1) */}
                <span style={{
                  padding: '4px 8px', borderRadius: '4px', background: '#0f172a',
                  border: '1px solid #334155', color: '#a78bfa', fontSize: '12px',
                  fontWeight: 600, fontFamily: 'monospace',
                }}>{cmsdEntity}</span>

                <div style={{ flex: 1 }} />

                {editSaving && (
                  <span style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span style={{ display: 'inline-block', width: '8px', height: '8px', border: '2px solid #64748b', borderTopColor: '#93c5fd', borderRadius: '50%', animation: 'spin 0.6s linear infinite' }} />
                    Saving...
                  </span>
                )}

                {mappingConfirmed ? (
                  <span style={{ fontSize: '11px', color: '#86efac', background: '#14532d', padding: '4px 10px', borderRadius: '4px', fontWeight: 600, whiteSpace: 'nowrap' }}>✓ Confirmed</span>
                ) : confirmPending ? (
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <button onClick={handleEditMapping} style={{ padding: '5px 12px', borderRadius: '4px', border: '1px solid #f59e0b', background: '#422006', color: '#fde68a', cursor: 'pointer', fontSize: '11px', fontWeight: 700, whiteSpace: 'nowrap' }}>✏️ Edit</button>
                    <button onClick={handleSaveAndContinue} disabled={confirmLoading} style={{ padding: '5px 12px', borderRadius: '4px', border: 'none', background: confirmLoading ? '#334155' : '#22c55e', color: confirmLoading ? '#64748b' : '#fff', cursor: confirmLoading ? 'not-allowed' : 'pointer', fontSize: '11px', fontWeight: 700, whiteSpace: 'nowrap' }}>{confirmLoading ? 'Saving...' : '✓ Save & Continue'}</button>
                  </div>
                ) : (
                  <button onClick={handleConfirmMapping} disabled={!allFieldsAllInstancesApproved}
                    title={!allFieldsAllInstancesApproved ? 'All fields must be approved on all instances' : 'Confirm this mapping'}
                    style={{ padding: '5px 14px', borderRadius: '4px', border: 'none', background: !allFieldsAllInstancesApproved ? '#334155' : '#22c55e', color: !allFieldsAllInstancesApproved ? '#64748b' : '#fff', cursor: !allFieldsAllInstancesApproved ? 'not-allowed' : 'pointer', fontSize: '11px', fontWeight: 700, whiteSpace: 'nowrap', opacity: !allFieldsAllInstancesApproved ? 0.6 : 1 }}>
                    {allFieldsAllInstancesApproved ? '✓ Confirm Mapping' : '🔒 Confirm Mapping'}
                  </button>
                )}

                {mappingResult.mapping?.error && (
                  <span style={{ fontSize: '11px', color: '#fca5a5', background: '#7f1d1d', padding: '3px 8px', borderRadius: '4px' }}>{mappingResult.mapping.error}</span>
                )}
              </div>

              {/* ── Dependency hint row ── */}
              {inferredDeps.length > 0 && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  padding: '6px 12px', marginBottom: '10px',
                  background: '#1e1b4b', borderRadius: '6px',
                  border: '1px solid #3730a3',
                }}>
                  <span style={{ fontSize: '11px', color: '#a5b4fc', fontWeight: 600 }}>
                    Depends on:
                  </span>
                  {inferredDeps.map(dep => (
                    <span key={dep} style={{
                      padding: '2px 8px', borderRadius: '10px',
                      background: '#0f172a', color: '#93c5fd',
                      fontSize: '11px', fontFamily: 'monospace',
                      border: existingEntities.has(dep) ? '1px solid #22c55e' : '1px solid #f59e0b',
                    }}>
                      {dep} {existingEntities.has(dep) ? '✓' : '(not yet mapped)'}
                    </span>
                  ))}
                  <span style={{ fontSize: '10px', color: '#64748b', marginLeft: 'auto' }}>
                    Dependencies are inferred automatically
                  </span>
                </div>
              )}

              {/* ── Expandable endpoint chips ── */}
              {endpointsExpanded && (
                <div style={{ marginBottom: '14px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {approvedPayloadEntries.map((entry) => (
                    <div key={entry.index}>
                      <button onClick={() => setExpandedPayload(expandedPayload === entry.index ? null : entry.index)}
                        style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #334155', background: expandedPayload === entry.index ? '#1e293b' : '#0f172a', color: '#e2e8f0', cursor: 'pointer', fontSize: '12px', fontFamily: 'monospace', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ color: entry.payload?.status === 'success' ? '#22c55e' : '#ef4444', fontSize: '10px' }}>●</span>
                        {entry.label}
                        <span style={{ color: '#64748b', fontSize: '10px' }}>({entry.payload?.size_bytes ? `${(entry.payload.size_bytes / 1024).toFixed(1)}KB` : '—'})</span>
                      </button>
                      {expandedPayload === entry.index && entry.payload?.status === 'success' && (
                        <div style={{ marginTop: '6px', marginLeft: '4px' }}>
                          <PayloadViewer payload={entry.payload} onRetry={() => {}} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* ── Instance bar ── */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: '12px',
                marginBottom: '14px', padding: '8px 12px',
                background: '#1e293b', borderRadius: '8px',
                border: '1px solid #334155', flexWrap: 'wrap',
              }}>
                {/* Instance navigation */}
                {hasInstances ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Instance</span>

                    <button onClick={() => setCurrentInstanceIndex(prev => prev > 0 ? prev - 1 : instanceInfo!.count - 1)}
                      title="Previous instance (Ctrl+Left)"
                      style={{ padding: '4px 7px', borderRadius: '4px', border: '1px solid #475569', background: '#1e293b', color: '#93c5fd', cursor: 'pointer', fontSize: '11px', fontWeight: 600, lineHeight: 1 }}>
                      &#9664;
                    </button>

                    <span style={{
                      color: '#f1f5f9', fontSize: '13px', fontWeight: 600,
                      fontFamily: 'monospace', minWidth: '40px', textAlign: 'center',
                    }}>
                      {Math.min(currentInstanceIndex, instanceInfo!.count - 1) + 1}
                    </span>

                    <span style={{ color: '#64748b', fontSize: '13px' }}>of {instanceInfo!.count}</span>

                    <button onClick={() => setCurrentInstanceIndex(prev => prev < instanceInfo!.count - 1 ? prev + 1 : 0)}
                      title="Next instance (Ctrl+Right)"
                      style={{ padding: '4px 7px', borderRadius: '4px', border: '1px solid #475569', background: '#1e293b', color: '#93c5fd', cursor: 'pointer', fontSize: '11px', fontWeight: 600, lineHeight: 1 }}>
                      &#9654;
                    </button>

                    <code style={{
                      color: '#86efac', background: '#0f172a',
                      padding: '4px 10px', borderRadius: '4px',
                      fontSize: '12px', fontFamily: 'monospace', fontWeight: 600,
                    }}>
                      {currentIdentifier}
                    </code>

                    {(() => {
                      const fields = mappingResult?.mapping?.mapping ?? {};
                      const fieldNames = Object.keys(fields);
                      const allApproved = fieldNames.length > 0 && fieldNames.every(f => (currentFieldStatuses[f] || 'pending') === 'approved');
                      return (
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button onClick={handleApproveAllFields}
                            title={allApproved ? 'Revert all fields to pending' : 'Approve all mapped fields for this instance'}
                            style={{
                              padding: '4px 12px', borderRadius: '4px',
                              border: allApproved ? '1px solid #f59e0b' : '1px solid #22c55e',
                              background: allApproved ? '#422006' : '#14532d',
                              color: allApproved ? '#fde68a' : '#86efac',
                              cursor: 'pointer', fontSize: '11px', fontWeight: 600, whiteSpace: 'nowrap',
                            }}>
                            {allApproved ? '↩ Revert All' : '✓ Approve All'}
                          </button>
                          {devMode && instanceInfo && instanceInfo.count > 1 && (
                            <button onClick={handleApproveAllInstances}
                              title={allFieldsAllInstancesApproved ? 'Revert all instances to pending' : `Approve all fields across ALL ${instanceInfo.count} instances`}
                              style={{
                                padding: '4px 12px', borderRadius: '4px',
                                border: allFieldsAllInstancesApproved ? '1px solid #f59e0b' : '1px solid #818cf8',
                                background: allFieldsAllInstancesApproved ? '#422006' : '#1e1b4b',
                                color: allFieldsAllInstancesApproved ? '#fde68a' : '#a5b4fc',
                                cursor: 'pointer', fontSize: '11px', fontWeight: 600, whiteSpace: 'nowrap',
                              }}>
                              {allFieldsAllInstancesApproved ? '↩ Revert All Instances' : `✓ Approve All ${instanceInfo.count} Instances`}
                            </button>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                ) : (
                  <span style={{ fontSize: '12px', color: '#64748b' }}>
                    {mappedFieldCount > 0 ? `${mappedFieldCount} fields mapped` : 'No instances detected'}
                  </span>
                )}

                {/* Stats */}
                <div style={{ marginLeft: 'auto', display: 'flex', gap: '12px', alignItems: 'center' }}>
                  {instanceInfo && instanceInfo.count > 1 && (() => {
                    const fields = mappingResult?.mapping?.mapping ?? {};
                    const fieldNames = Object.keys(fields);
                    let approvedInstances = 0;
                    for (let i = 0; i < instanceInfo.count; i++) {
                      if (fieldNames.length > 0 && fieldNames.every(f => (fieldStatuses[`${i}:${f}`] || 'pending') === 'approved')) {
                        approvedInstances++;
                      }
                    }
                    return (
                      <span style={{ fontSize: '11px', color: approvedInstances === instanceInfo.count ? '#86efac' : '#fde68a' }}>
                        {approvedInstances}/{instanceInfo.count} instance{instanceInfo.count !== 1 ? 's' : ''} approved
                      </span>
                    );
                  })()}
                  <span style={{ fontSize: '12px', color: '#64748b' }}>
                    {mappedFieldCount} field{mappedFieldCount !== 1 ? 's' : ''}
                    {unmappedCount > 0 && <span style={{ color: '#f59e0b' }}> &middot; {unmappedCount} unmapped</span>}
                  </span>
                </div>
              </div>

              {/* ── Mapping Table ── */}
              <MappingTable
                mapping={liveMapping}
                cmsdEntity={analyzedEntity || cmsdEntity}
                availableEndpoints={availableEndpoints}
                onMappingChange={handleMappingChange}
                onAddMapping={handleAddMapping}
                reviewMode
                fieldStatuses={currentFieldStatuses}
                fieldComments={currentFieldComments}
                onStatusChange={handleStatusChange}
                onCommentChange={handleCommentChange}
                typeValidation={typeValidation}
              />

              {/* Reanalyze Flagged button */}
              {Object.values(fieldStatuses).some(s => s === 'flagged') && (
                <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <button onClick={handleReviewReanalyze} disabled={reanalyzeLoading}
                    style={{
                      padding: '10px 24px', borderRadius: '6px', border: 'none',
                      background: reanalyzeLoading ? '#334155' : '#f59e0b',
                      color: reanalyzeLoading ? '#64748b' : '#0f172a',
                      cursor: reanalyzeLoading ? 'not-allowed' : 'pointer',
                      fontSize: '13px', fontWeight: 700,
                      display: 'flex', alignItems: 'center', gap: '8px',
                    }}>
                    {reanalyzeLoading ? (
                      <><span style={{ display: 'inline-block', width: '12px', height: '12px', border: '2px solid #64748b', borderTopColor: '#93c5fd', borderRadius: '50%', animation: 'spin 0.6s linear infinite' }} /> Reanalyzing...</>
                    ) : (
                      <>⚡ Reanalyze {Object.values(fieldStatuses).filter(s => s === 'flagged').length} Flagged Field{Object.values(fieldStatuses).filter(s => s === 'flagged').length !== 1 ? 's' : ''}</>
                    )}
                  </button>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>
                    Only flagged fields will be sent to the LLM with your comments. Approved fields will stay unchanged.
                  </span>
                </div>
              )}

              {/* ── Smart Reanalyze with Guidance ── */}
              {mappedFieldCount > 0 && (
                <div style={{ marginBottom: '16px' }}>
                  {guidanceOpen ? (
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                      <input
                        value={guidanceInput}
                        onChange={e => setGuidanceInput(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') handleSmartReanalyze(); if (e.key === 'Escape') { setGuidanceOpen(false); setGuidanceInput(''); } }}
                        placeholder="e.g., MTTR should come from /incidents API, use seconds for cycle_time..."
                        style={{
                          flex: 1, minWidth: '280px', background: '#0f172a', border: '1px solid #475569',
                          borderRadius: '6px', padding: '10px 12px', color: '#f1f5f9', fontSize: '13px',
                          fontFamily: 'monospace', boxSizing: 'border-box',
                        }}
                        autoFocus
                      />
                      <button onClick={handleSmartReanalyze} disabled={guidanceLoading || !guidanceInput.trim()}
                        style={{
                          padding: '10px 18px', borderRadius: '6px', border: 'none',
                          background: guidanceLoading || !guidanceInput.trim() ? '#334155' : '#7c3aed',
                          color: guidanceLoading || !guidanceInput.trim() ? '#64748b' : '#fff',
                          cursor: guidanceLoading || !guidanceInput.trim() ? 'not-allowed' : 'pointer',
                          fontSize: '13px', fontWeight: 700, whiteSpace: 'nowrap',
                          display: 'flex', alignItems: 'center', gap: '6px',
                        }}>
                        {guidanceLoading ? (
                          <><span style={{ display: 'inline-block', width: '12px', height: '12px', border: '2px solid #64748b', borderTopColor: '#93c5fd', borderRadius: '50%', animation: 'spin 0.6s linear infinite' }} /> Analyzing...</>
                        ) : (
                          <>🧠 Apply Guidance</>
                        )}
                      </button>
                      <button onClick={() => { setGuidanceOpen(false); setGuidanceInput(''); }}
                        style={{
                          padding: '10px 12px', borderRadius: '6px', border: '1px solid #475569',
                          background: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: '13px',
                        }}>
                        ✖
                      </button>
                    </div>
                  ) : (
                    <button onClick={() => setGuidanceOpen(true)}
                      style={{
                        padding: '8px 16px', borderRadius: '6px', border: '1px solid #475569',
                        background: '#1e3a5f', color: '#93c5fd', cursor: 'pointer',
                        fontSize: '12px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px',
                      }}>
                      🧠 Re-analyze with Guidance
                    </button>
                  )}
                </div>
              )}

              {/* ── Entity Preview (collapsible, per-instance) ── */}
              {mappedFieldCount > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <button onClick={() => setPreviewExpanded(!previewExpanded)}
                    style={{ padding: '4px 0', border: 'none', background: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: '12px', fontWeight: 500, marginBottom: previewExpanded ? '8px' : '0' }}>
                    {previewExpanded ? '▾' : '▸'} Entity Preview
                    {currentInstanceData && <span style={{ color: '#86efac', fontWeight: 400 }}> — live instance</span>}
                  </button>
                  {previewExpanded && (
                    <EntityPreview
                      key={currentInstanceIndex}
                      mapping={mappingResult.mapping}
                      cmsdEntity={analyzedEntity || cmsdEntity}
                      instances={mappingResult.mapping?.instances}
                      changedFields={changedFields}
                      instanceData={currentInstanceData}
                    />
                  )}
                </div>
              )}

              {/* ── Confirmed: next-step prompt ── */}
              {mappingConfirmed && (
                <div style={{
                  marginBottom: '16px', padding: '14px 18px',
                  background: '#064e3b', borderRadius: '8px',
                  border: '1px solid #22c55e',
                  display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap',
                }}>
                  <span style={{ fontSize: '20px' }}>✓</span>
                  <div style={{ flex: 1 }}>
                    <p style={{ margin: 0, color: '#86efac', fontSize: '13px', fontWeight: 600 }}>
                      Mapping confirmed — "{dataPointName || 'Untitled Data Point'}" → {analyzedEntity || cmsdEntity}
                    </p>
                    <p style={{ margin: '4px 0 0', color: '#6ee7b7', fontSize: '12px' }}>
                      Go to <strong>Review Queue</strong> to manage and generate instances, or stay here to map another entity.
                    </p>
                  </div>
                  <button
                    onClick={() => onNavigateToQueue?.()}
                    style={{
                      padding: '6px 16px', borderRadius: '6px', border: '1px solid #22c55e',
                      background: 'transparent', color: '#86efac', cursor: 'pointer',
                      fontSize: '13px', fontWeight: 600, whiteSpace: 'nowrap',
                    }}
                  >
                    Go to Review Queue →
                  </button>
                </div>
              )}

              {/* ── Footer ── */}
              {((mappingResult.mapping?.instances?.count_path && mappingResult.mapping?.instances?.key_field) || unmappedCount > 0) && (
                <div style={{ fontSize: '12px', color: '#64748b', display: 'flex', gap: '16px', flexWrap: 'wrap', paddingTop: '8px', borderTop: '1px solid #1e293b' }}>
                  {mappingResult.mapping?.instances?.count_path && (
                    <span>
                      Source array: <code style={codeChip}>{mappingResult.mapping.instances.count_path}</code>
                      {mappingResult.mapping.instances.key_field && <span> keyed by <code style={codeChip}>{mappingResult.mapping.instances.key_field}</code></span>}
                      {instanceInfo && <span> &middot; {instanceInfo.count} instances</span>}
                    </span>
                  )}
                  {unmappedCount > 0 && (
                    <span style={{ color: '#f59e0b' }}>
                      {unmappedCount} unmapped &mdash; click <strong style={{ color: '#fde68a' }}>+ Add</strong> in table footer
                    </span>
                  )}
                </div>
              )}

              {/* ── Mapping Chat (floating widget) ── */}
              <MappingChat
                dataPointName={dataPointName || 'Untitled Data Point'}
                currentMapping={mappingResult.mapping}
                onSendMessage={handleChatSend}
                isOpen={chatOpen}
                onToggle={() => setChatOpen(!chatOpen)}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SpinnerLarge() {
  return (
    <span style={{ display: 'inline-block', width: '32px', height: '32px', border: '3px solid #334155', borderTopColor: '#93c5fd', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
  );
}

const CMSD_ENTITIES = [
  'Resource', 'ResourceClass', 'PartType', 'Part', 'BillOfMaterials',
  'BOMComponent', 'ProcessPlan', 'Process', 'Order', 'OrderLine',
  'Calendar', 'Shift', 'Break', 'Holiday', 'Connection',
  'Job', 'InventoryItem', 'MaintenancePlan',
];

// Static dependency map: entity → list of entity types it depends on
// Based on actual CMSD Pydantic model fields. In the CMSD standard, most
// cross-entity references are via nested objects (e.g. Order.order_lines is
// List[OrderLine], not a top-level FK). V1 maps only flat/top-level fields,
// so most entities have NO direct dependencies. Dependencies are primarily
// inferred from API field names (e.g. if an API returns "resource_id" in an
// order payload, the LLM maps it and _infer_dependencies picks it up).
const CMSD_ENTITY_DEPS: Record<string, string[]> = {
  'Resource': [],
  'ResourceClass': [],
  'Calendar': [],
  'Shift': [],
  'Break': [],
  'Holiday': [],
  'PartType': [],
  'Part': [],
  'Connection': [],
  'ProcessPlan': [],
  'Process': [],
  'Order': [],
  'OrderLine': [],
  'BillOfMaterials': [],
  'BillOfMaterialsComponent': [],
  'Job': [],
  'InventoryItem': [],
  'MaintenancePlan': [],
};

interface EntityTierPickerProps {
  cmsdEntity: string;
  onSelect: (entity: string) => void;
  existingEntities: Set<string>;
}

function EntityTierPicker({ cmsdEntity, onSelect, existingEntities }: EntityTierPickerProps) {
  const unmapped = (filter: (e: string) => boolean) =>
    CMSD_ENTITIES.filter(e => filter(e) && !existingEntities.has(e));

  const independent = CMSD_ENTITIES.filter(e => (CMSD_ENTITY_DEPS[e] || []).length === 0);
  const dependent = CMSD_ENTITIES.filter(e => (CMSD_ENTITY_DEPS[e] || []).length > 0);

  const readyDeps = dependent.filter(e => {
    const deps = CMSD_ENTITY_DEPS[e] || [];
    return deps.every(d => existingEntities.has(d));
  });
  const needsDeps = dependent.filter(e => {
    const deps = CMSD_ENTITY_DEPS[e] || [];
    return !deps.every(d => existingEntities.has(d));
  });

  return (
    <div style={{
      background: '#1e293b', borderRadius: '8px', border: '1px solid #334155',
      padding: '12px 16px', marginBottom: '14px',
    }}>
      <div style={{ marginBottom: '6px' }}>
        <span style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Recommendation: which entity to map next
        </span>
      </div>

      {/* Independent — always ready */}
      <div style={{ marginBottom: '8px' }}>
        <span style={{ fontSize: '11px', color: '#86efac', fontWeight: 600 }}>✓ Ready (no dependencies)</span>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '4px' }}>
          {unmapped(e => independent.includes(e)).slice(0, 8).map(e => (
            <button key={e} onClick={() => onSelect(e)} style={{
              padding: '3px 10px', borderRadius: '14px',
              border: cmsdEntity === e ? '2px solid #22c55e' : '1px solid #166534',
              background: cmsdEntity === e ? '#14532d' : 'transparent',
              color: cmsdEntity === e ? '#86efac' : '#6ee7b7',
              cursor: 'pointer', fontSize: '11px', fontWeight: cmsdEntity === e ? 700 : 500,
            }}>
              {e}
            </button>
          ))}
          {existingEntities.size > 0 && independent.filter(e => existingEntities.has(e)).length > 0 && (
            <span style={{ fontSize: '10px', color: '#475569', alignSelf: 'center' }}>
              +{independent.filter(e => existingEntities.has(e)).length} already mapped
            </span>
          )}
        </div>
      </div>

      {/* Dependent but ready */}
      {unmapped(e => readyDeps.includes(e)).length > 0 && (
        <div style={{ marginBottom: '8px' }}>
          <span style={{ fontSize: '11px', color: '#a5b4fc', fontWeight: 600 }}>
            ◉ Ready (dependencies satisfied)
          </span>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '4px' }}>
            {unmapped(e => readyDeps.includes(e)).map(e => {
              const deps = CMSD_ENTITY_DEPS[e] || [];
              return (
                <button key={e} onClick={() => onSelect(e)} style={{
                  padding: '3px 10px', borderRadius: '14px',
                  border: cmsdEntity === e ? '2px solid #818cf8' : '1px solid #3730a3',
                  background: cmsdEntity === e ? '#1e1b4b' : 'transparent',
                  color: cmsdEntity === e ? '#a5b4fc' : '#818cf8',
                  cursor: 'pointer', fontSize: '11px', fontWeight: cmsdEntity === e ? 700 : 500,
                }} title={`Depends on: ${deps.join(', ')}`}>
                  {e}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Needs dependencies */}
      {unmapped(e => needsDeps.includes(e)).length > 0 && (
        <div style={{ marginBottom: '4px' }}>
          <span style={{ fontSize: '11px', color: '#fde68a', fontWeight: 600 }}>
            🔒 Needs dependencies first
          </span>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '4px' }}>
            {unmapped(e => needsDeps.includes(e)).map(e => {
              const deps = CMSD_ENTITY_DEPS[e] || [];
              const missing = deps.filter(d => !existingEntities.has(d));
              return (
                <button key={e} onClick={() => onSelect(e)} style={{
                  padding: '3px 10px', borderRadius: '14px',
                  border: cmsdEntity === e ? '2px solid #f59e0b' : '1px solid #78350f',
                  background: cmsdEntity === e ? '#422006' : 'transparent',
                  color: cmsdEntity === e ? '#fde68a' : '#fbbf24',
                  cursor: 'pointer', fontSize: '11px', fontWeight: cmsdEntity === e ? 700 : 500,
                }} title={`Needs: ${deps.join(', ')} (missing: ${missing.join(', ')})`}>
                  {e}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

const codeChip: React.CSSProperties = {
  color: '#f1f5f9', background: '#1e293b', padding: '1px 6px', borderRadius: '3px', fontSize: '11px', fontFamily: 'monospace',
};

const labelStyle: React.CSSProperties = {
  fontSize: '11px', color: '#94a3b8', display: 'block', marginBottom: '4px', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px',
};
const inputStyle: React.CSSProperties = {
  width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '6px 10px', color: '#f1f5f9', fontSize: '13px', fontFamily: 'monospace', boxSizing: 'border-box', height: '42px',
};
const selectStyle: React.CSSProperties = {
  width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '6px 10px', color: '#f1f5f9', fontSize: '13px', height: '42px', boxSizing: 'border-box',
};
