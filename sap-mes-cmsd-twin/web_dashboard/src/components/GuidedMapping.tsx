import { useState } from 'react';
import FieldMappingTable from './FieldMappingTable';
import MappingChat from './MappingChat';
import { agentApi } from '../services/agentApi';
import { SourceData } from './SourceCard';

interface GuidedMappingProps {
  sources: SourceData[];
  onComplete: () => void;
}

interface EndpointEntry {
  source_id: string;
  endpoint: string;
}

const DATA_POINTS = [
  { name: 'Resources', cmsd: 'Resource', sapHint: '/resources', mesHint: '/resource-status' },
  { name: 'Resource Classes', cmsd: 'ResourceClass', sapHint: '/resource-classes' },
  { name: 'Part Types', cmsd: 'PartType', sapHint: '/part-types' },
  { name: 'Parts', cmsd: 'Part', sapHint: '/parts' },
  { name: 'Bill of Materials', cmsd: 'BillOfMaterials', sapHint: '/boms' },
  { name: 'Process Plans', cmsd: 'ProcessPlan', sapHint: '/process-plans' },
  { name: 'Orders', cmsd: 'Order', sapHint: '/orders' },
  { name: 'Calendars', cmsd: 'Calendar', sapHint: '/calendars' },
  { name: 'Connections', cmsd: 'Connection', sapHint: '/connections' },
  { name: 'Jobs', cmsd: 'Job', mesHint: '/jobs' },
  { name: 'Inventory', cmsd: 'InventoryItem', mesHint: '/inventory' },
  { name: 'Maintenance Plans', cmsd: 'MaintenancePlan', mesHint: '/incidents' },
];

export default function GuidedMapping({ sources, onComplete }: GuidedMappingProps) {
  const [activeStep, setActiveStep] = useState(0);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mappings, setMappings] = useState<Record<string, any>>({});
  const [generating, setGenerating] = useState<Record<string, boolean>>({});
  const [chatOpen, setChatOpen] = useState(false);
  const [chatUpdatedMapping, setChatUpdatedMapping] = useState<any>(null);
  const [confirmCount, setConfirmCount] = useState(0);
  const [rawPayloads, setRawPayloads] = useState<Record<string, any[]>>({});
  const [showRawPayload, setShowRawPayload] = useState(false);

  const dp = DATA_POINTS[activeStep];
  const currentMapping = mappings[dp.name]?.mapping || {};
  const unmappedFields = mappings[dp.name]?.unmapped_fields || [];
  const isConfirmed = mappings[dp.name]?.confirmed || false;

  const findDefaultSource = (isMes: boolean): string => {
    for (const s of sources) {
      const n = s.name.toLowerCase();
      if (isMes && (n.includes('mes') || !n.includes('sap'))) return s.id;
      if (!isMes && n.includes('sap')) return s.id;
    }
    return sources[0]?.id || '';
  };

  const getDefaultEndpoint = (): string => dp.sapHint || dp.mesHint || '';

  const [stepState, setStepState] = useState<Record<string, { endpoints: EndpointEntry[] }>>({});

  const currentEndpoints: EndpointEntry[] = (() => {
    const existing = stepState[dp.name]?.endpoints;
    if (existing && existing.length > 0) return existing;
    const isMes = ['Jobs', 'Inventory', 'Maintenance Plans'].includes(dp.name);
    return [{ source_id: findDefaultSource(isMes), endpoint: getDefaultEndpoint() }];
  })();

  const setEndpoints = (endpoints: EndpointEntry[]) => {
    setStepState(prev => ({ ...prev, [dp.name]: { endpoints } }));
  };

  const addEndpoint = () => {
    const isMes = ['Jobs', 'Inventory', 'Maintenance Plans'].includes(dp.name);
    setEndpoints([...currentEndpoints, { source_id: findDefaultSource(isMes), endpoint: '' }]);
  };

  const updateEndpoint = (index: number, patch: Partial<EndpointEntry>) => {
    const updated = [...currentEndpoints];
    updated[index] = { ...updated[index], ...patch };
    setEndpoints(updated);
  };

  const removeEndpoint = (index: number) => {
    if (currentEndpoints.length <= 1) return;
    setEndpoints(currentEndpoints.filter((_, i) => i !== index));
  };

  const analyze = async () => {
    setAnalyzing(true);
    setError(null);
    setChatUpdatedMapping(null);
    try {
      const validEndpoints = currentEndpoints.filter(ep => ep.endpoint.trim());
      if (validEndpoints.length === 0) {
        setError('Please add at least one API endpoint.');
        return;
      }
      const result = await agentApi.analyzeMapping({
        source_id: validEndpoints[0].source_id,
        data_point_name: dp.name,
        cmsd_entity: dp.cmsd,
        api_endpoint: validEndpoints[0].endpoint,
        endpoints: validEndpoints,
      });
      const payloads = result.raw_payloads || [];
      if (result.raw_payload) {
        payloads.push({
          endpoint: validEndpoints[0].endpoint,
          url: result.payload_summary?.url || validEndpoints[0].endpoint,
          payload: result.raw_payload,
          status_code: result.payload_summary?.status_code,
        });
      }
      setRawPayloads(prev => ({ ...prev, [dp.name]: payloads }));
      setMappings(prev => ({
        ...prev,
        [dp.name]: { ...result.proposed_mapping, confirmed: false },
      }));
    } catch (e: any) {
      setError(e.message);
    }
    setAnalyzing(false);
  };

  const editMapping = (field: string, updates: any) => {
    setMappings(prev => {
      const m = structuredClone(prev[dp.name] || {});
      m.mapping = m.mapping || {};
      m.mapping[field] = { ...m.mapping[field], ...updates, confidence: updates.confidence || 'manual' };
      return { ...prev, [dp.name]: m };
    });
  };

  const removeMapping = (field: string) => {
    setMappings(prev => {
      const m = structuredClone(prev[dp.name] || {});
      m.mapping = m.mapping || {};
      delete m.mapping[field];
      return { ...prev, [dp.name]: m };
    });
  };

  const applyChatUpdate = (updatedMapping: any) => {
    setChatUpdatedMapping(updatedMapping);
    setMappings(prev => ({ ...prev, [dp.name]: { ...prev[dp.name], ...updatedMapping, confirmed: false } }));
  };

  const smartReanalyze = async (guidance: string) => {
    setAnalyzing(true);
    setError(null);
    try {
      const m = mappings[dp.name];
      const result = await agentApi.smartReanalyze({
        data_point_name: dp.name,
        cmsd_entity: dp.cmsd,
        current_mapping: m,
        user_guidance: guidance,
      });
      setMappings(prev => ({
        ...prev,
        [dp.name]: { ...result.proposed_mapping, confirmed: false },
      }));
    } catch (e: any) {
      setError(`Smart reanalyze failed: ${e.message}`);
    }
    setAnalyzing(false);
  };

  const confirmAndGenerate = async () => {
    const m = mappings[dp.name];
    if (!m) return;
    setGenerating(prev => ({ ...prev, [dp.name]: true }));
    try {
      const id = `confirm-${dp.name}-${Date.now()}`;
      await agentApi.confirmMapping(id, { mapping: m });
      setMappings(prev => ({ ...prev, [dp.name]: { ...m, confirmed: true } }));
      setConfirmCount(c => c + 1);
    } catch (e: any) {
      setError(`Confirmation failed: ${e.message}`);
    }
    setGenerating(prev => ({ ...prev, [dp.name]: false }));
  };

  const chatSend = async (msg: string): Promise<string> => {
    const result = await agentApi.chatMapping({
      data_point_name: dp.name,
      current_mapping: currentMapping,
      user_question: msg,
    });
    return result.response || 'No response';
  };

  const allConfirmed = confirmCount >= DATA_POINTS.length;

  return (
    <div>
      {/* Sub-step navigation */}
      <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', padding: '8px 0', marginBottom: '16px' }}>
        {DATA_POINTS.map((p, i) => {
          const done = mappings[p.name]?.confirmed;
          const active = i === activeStep;
          return (
            <button key={p.name} onClick={() => setActiveStep(i)}
              style={{
                padding: '6px 14px', borderRadius: '16px', border: active ? '2px solid #3b82f6' : '1px solid #334155',
                background: done ? '#064e3b' : active ? '#1e293b' : '#0f172a',
                color: done ? '#4ade80' : active ? '#f1f5f9' : '#64748b',
                cursor: 'pointer', fontSize: '12px', whiteSpace: 'nowrap', fontWeight: active ? 600 : 400,
              }}>
              {done ? '✓' : ''} {p.name}
            </button>
          );
        })}
      </div>

      {/* Current step header */}
      <div style={{ background: '#1e293b', borderRadius: '8px', padding: '16px', marginBottom: '16px', border: '1px solid #334155' }}>
        <h3 style={{ margin: 0, color: '#f1f5f9', fontSize: '16px' }}>{dp.cmsd} — {dp.name}</h3>

        {/* Multi-endpoint list */}
        {currentEndpoints.map((ep, i) => (
          <div key={i} style={{ display: 'flex', gap: '8px', marginTop: i === 0 ? '12px' : '6px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '160px' }}>
              {i === 0 && <label style={{ fontSize: '11px', color: '#94a3b8', display: 'block', marginBottom: '2px' }}>Data Source</label>}
              <select value={ep.source_id} onChange={e => updateEndpoint(i, { source_id: e.target.value })}
                style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '6px 8px', color: '#f1f5f9', fontSize: '13px' }}>
                {sources.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div style={{ flex: 2, minWidth: '220px' }}>
              {i === 0 && <label style={{ fontSize: '11px', color: '#94a3b8', display: 'block', marginBottom: '2px' }}>API Endpoint</label>}
              <input value={ep.endpoint} onChange={e => updateEndpoint(i, { endpoint: e.target.value })}
                placeholder="/api/endpoint" style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '6px 8px', color: '#f1f5f9', fontSize: '13px', boxSizing: 'border-box' }} />
            </div>
            {currentEndpoints.length > 1 && (
              <button onClick={() => removeEndpoint(i)}
                style={{ padding: '6px 10px', background: '#7f1d1d', color: '#fca5a5', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}>
                ×
              </button>
            )}
          </div>
        ))}

        <div style={{ display: 'flex', gap: '10px', marginTop: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button onClick={addEndpoint}
            style={{ padding: '6px 14px', background: '#1e3a5f', color: '#93c5fd', border: '1px dashed #475569', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>
            + Add API
          </button>
          <button onClick={analyze} disabled={analyzing}
            style={{ padding: '8px 20px', borderRadius: '6px', border: 'none', background: analyzing ? '#334155' : '#3b82f6', color: '#fff', cursor: analyzing ? 'not-allowed' : 'pointer', fontSize: '13px', fontWeight: 600 }}>
            {analyzing ? '⏳ Analyzing…' : '🔍 Analyze'}
          </button>
        </div>
        {error && <div style={{ marginTop: '8px', padding: '8px 12px', background: '#7f1d1d', borderRadius: '6px', color: '#fca5a5', fontSize: '12px' }}>❌ {error}</div>}
      </div>

      {/* Raw Payload Viewer */}
      {rawPayloads[dp.name] && rawPayloads[dp.name].length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <button onClick={() => setShowRawPayload(!showRawPayload)}
            style={{
              padding: '8px 16px', background: '#1e293b', border: '1px solid #334155',
              borderRadius: '6px', color: '#94a3b8', cursor: 'pointer', fontSize: '12px',
              display: 'flex', alignItems: 'center', gap: '6px', width: '100%',
            }}>
            <span>{showRawPayload ? '▲' : '▼'}</span>
            📄 Raw API Response{rawPayloads[dp.name].length > 1 ? 's' : ''} ({rawPayloads[dp.name].length} endpoint{rawPayloads[dp.name].length > 1 ? 's' : ''})
          </button>
          {showRawPayload && (
            <div style={{ marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {rawPayloads[dp.name].map((rp: any, ri: number) => (
                <div key={ri} style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', overflow: 'hidden' }}>
                  <div style={{ padding: '6px 12px', background: '#1e293b', borderBottom: '1px solid #334155', fontSize: '11px', color: '#94a3b8', display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontFamily: 'monospace', color: '#a78bfa' }}>{rp.url || rp.endpoint}</span>
                    {rp.status_code && <span style={{ color: rp.status_code < 400 ? '#4ade80' : '#fca5a5' }}>HTTP {rp.status_code}</span>}
                  </div>
                  <pre style={{
                    padding: '12px', margin: 0, overflow: 'auto', maxHeight: '280px',
                    color: '#e2e8f0', fontSize: '11px', fontFamily: 'monospace',
                    lineHeight: '1.5', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                  }}>
                    {JSON.stringify(rp.payload, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Mapping Table */}
      <FieldMappingTable
        mapping={currentMapping}
        cmsdEntity={dp.cmsd}
        unmappedFields={unmappedFields}
        onEdit={editMapping}
        onRemove={removeMapping}
        onConfirm={confirmAndGenerate}
        onReanalyze={analyze}
        onSmartReanalyze={smartReanalyze}
        isConfirmed={isConfirmed}
        isGenerating={generating[dp.name] || false}
      />

      {/* Chat widget */}
      <MappingChat
        dataPointName={dp.name}
        currentMapping={currentMapping}
        onSendMessage={chatSend}
        onApplyMappingUpdate={applyChatUpdate}
        isOpen={chatOpen}
        onToggle={() => setChatOpen(!chatOpen)}
      />

      {/* Bottom navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderTop: '1px solid #334155', marginTop: '16px' }}>
        <button onClick={() => setActiveStep(i => Math.max(0, i - 1))} disabled={activeStep === 0}
          style={{ padding: '10px 20px', background: '#334155', color: '#94a3b8', border: 'none', borderRadius: '6px', cursor: activeStep === 0 ? 'not-allowed' : 'pointer', fontSize: '13px' }}>
          ← Previous
        </button>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <span style={{ fontSize: '13px', color: '#94a3b8' }}>
            Step {activeStep + 1}/{DATA_POINTS.length}
          </span>
          {activeStep < DATA_POINTS.length - 1 ? (
            <button onClick={() => setActiveStep(i => Math.min(DATA_POINTS.length - 1, i + 1))}
              style={{ padding: '10px 20px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '13px' }}>
              Next →
            </button>
          ) : (
            <button onClick={onComplete} disabled={!allConfirmed}
              style={{ padding: '10px 24px', borderRadius: '6px', border: 'none',
                background: allConfirmed ? '#22c55e' : '#334155', color: allConfirmed ? '#fff' : '#64748b',
                cursor: allConfirmed ? 'pointer' : 'not-allowed', fontSize: '14px', fontWeight: 600 }}>
              ✅ Complete Setup
            </button>
          )}
        </div>
      </div>
    </div>
  );
}