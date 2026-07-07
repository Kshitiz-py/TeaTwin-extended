import { useState, useEffect } from 'react';
import SourceCard, { SourceData } from './SourceCard';
import { agentApi } from '../services/agentApi';
import EntitySetBrowser from './EntitySetBrowser';

interface ConnectSourcesProps {
  onSourcesComplete: (sources: SourceData[]) => void;
  initialSources?: SourceData[];
  agentConnected?: boolean;
}

export default function ConnectSources({ onSourcesComplete, initialSources }: ConnectSourcesProps) {
  const [sources, setSources] = useState<SourceData[]>(initialSources || []);
  const [indexing, setIndexing] = useState(false);
  const [indexResult, setIndexResult] = useState<string | null>(null);
  const [discovering, setDiscovering] = useState(false);
  const [discoveredSourceId, setDiscoveredSourceId] = useState<string | null>(null);
  const [selectedEntitySets, setSelectedEntitySets] = useState<string[]>([]);

  useEffect(() => {
    // Load existing sources on mount
    agentApi.getSources()
      .then(res => {
        if (res.sources?.length) setSources(res.sources);
      })
      .catch(() => {});
  }, []);

  const addSource = () => {
    const newSource: SourceData = {
      id: '',
      name: 'New Source',
      base_url: '',
      auth_type: 'none',
      status: 'configured',
    };
    setSources(prev => [...prev, newSource]);
  };

  const updateSource = async (updated: SourceData) => {
    if (!updated.id || updated.id === '') {
      // Create via API
      try {
        const created = await agentApi.createSource(updated);
        setSources(prev => prev.map(s => s.id === '' || s === updated ? created : s));
        setIndexResult(`Source "${created.name}" saved`);
      } catch (e) {
        setIndexResult('Failed to save source');
      }
      return;
    }
    // Update locally (and via API)
    try {
      await agentApi.createSource(updated); // same endpoint handles upsert
      setSources(prev => prev.map(s => s.id === updated.id ? updated : s));
    } catch {
      setSources(prev => prev.map(s => s.id === updated.id ? updated : s));
    }
  };

  const testSource = async (sourceId: string) => {
    if (!sourceId || sourceId === '') {
      // Save first, then test
      setIndexResult('Save the source first before testing');
      return;
    }
    const src = sources.find(s => s.id === sourceId);
    if (src) {
      setSources(prev => prev.map(s => s.id === sourceId ? { ...s, status: 'testing' } : s));
      try {
        const result = await agentApi.testSource(sourceId);
        setSources(prev => prev.map(s =>
          s.id === sourceId
            ? { ...s, status: result.success ? 'connected' : 'failed', latency_ms: result.latency_ms, last_tested: new Date().toISOString() }
            : s
        ));
      } catch {
        setSources(prev => prev.map(s => s.id === sourceId ? { ...s, status: 'failed' } : s));
      }
    }
  };

  const removeSource = async (sourceId: string) => {
    if (sourceId && sourceId !== '') {
      try { await agentApi.deleteSource(sourceId); } catch {}
    }
    setSources(prev => prev.filter(s => s.id !== sourceId));
  };

  const handleIndexRag = async () => {
    setIndexing(true);
    setIndexResult(null);
    try {
      const result = await agentApi.indexRag();
      setIndexResult(`Indexed ${result.documents_indexed} documents (${result.chunks_loaded} chunks)`);
    } catch (e: any) {
      setIndexResult(`Indexing failed: ${e.message}`);
    }
    setIndexing(false);
  };

  const connectedCount = sources.filter(s => s.status === 'connected').length;
  const canProceed = connectedCount > 0;

  const addMockSources = async () => {
    // Pre-fill Mock SAP source
    const sapSource: SourceData = {
      id: '',
      name: 'Mock SAP API',
      base_url: 'http://mock-sap-api:8001/api/sap/v1',
      auth_type: 'none',
      status: 'configured',
    };
    const mesSource: SourceData = {
      id: '',
      name: 'Mock MES API',
      base_url: 'http://mock-mes-api:8002/api/mes/v1',
      auth_type: 'none',
      status: 'configured',
    };
    // Save both via API
    try {
      const createdSap = await agentApi.createSource(sapSource);
      const createdMes = await agentApi.createSource(mesSource);
      setSources(prev => {
        const filtered = prev.filter(s => s.id !== createdSap.id && s.id !== createdMes.id);
        return [...filtered, createdSap, createdMes];
      });
      setIndexResult('Mock SAP & Mock MES sources added — click Test to verify connectivity');
    } catch (e: any) {
      setIndexResult(`Failed to add mock sources: ${e.message}`);
    }
  };

  const addRealSap = async () => {
    const sapSource: SourceData = {
      id: '',
      name: 'Real SAP (a33p) — API_PRODUCTION_ROUTING',
      base_url: 'https://a33p.ucc.cloud/sap/opu/odata/sap/API_PRODUCTION_ROUTING',
      auth_type: 'basic',
      username: '',
      password: '',
      extra_headers: { 'sap-client': '200' },
      status: 'configured',
    };
    try {
      const created = await agentApi.createSource(sapSource);
      setSources(prev => [...prev.filter(s => s.id !== created.id), created]);
      setIndexResult('Real SAP source added — enter your SAP username/password, Test, then Discover.');
    } catch (e: any) {
      setIndexResult(`Failed to add SAP source: ${e.message}`);
    }
  };

  const handleDiscoverSap = async () => {
    const sap = sources.find(s => /sap/i.test(s.name) && s.id);
    if (!sap) {
      setIndexResult('Add and save a SAP source first (e.g. "Real SAP (a33p)").');
      return;
    }
    setDiscovering(true);
    setIndexResult(null);
    try {
      const res = await agentApi.discoverSchema(sap.id);
      setDiscoveredSourceId(sap.id);
      setIndexResult(`Discovered ${res.entity_sets.length} entity sets; indexed ${res.chunks_indexed} source-schema chunks.`);
    } catch (e: any) {
      setIndexResult(`Discover failed: ${e.message}`);
    }
    setDiscovering(false);
  };

  const toggleEntitySet = (entitySet: string) =>
    setSelectedEntitySets(prev => prev.includes(entitySet) ? prev.filter(x => x !== entitySet) : [...prev, entitySet]);

  const handleNext = () => {
    onSourcesComplete(sources.filter(s => s.status === 'connected'));
  };

  return (
    <div>
      {/* Sources Grid */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h2 style={{ fontSize: '18px', color: '#f1f5f9', margin: 0 }}>
            Data Sources ({sources.length})
          </h2>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={handleIndexRag}
              disabled={indexing}
              style={{
                padding: '8px 16px', background: '#334155', color: '#94a3b8',
                border: '1px solid #475569', borderRadius: '6px', cursor: indexing ? 'not-allowed' : 'pointer',
                fontSize: '13px',
              }}
            >
              {indexing ? '⏳ Indexing...' : '📚 Index RAG Corpus'}
            </button>
            <button
              onClick={addMockSources}
              title="Pre-fill Mock SAP and Mock MES sources to test the setup wizard"
              style={{
                padding: '8px 16px', background: '#1e3a5f', color: '#93c5fd',
                border: '1px solid #3b82f6', borderRadius: '6px', cursor: 'pointer',
                fontSize: '13px', fontWeight: 500,
              }}
            >
              🧪 Mock APIs
            </button>
            <button
              onClick={addRealSap}
              title="Pre-fill a real SAP S/4HANA OData source (a33p, API_PRODUCTION_ROUTING, Basic auth)"
              style={{
                padding: '8px 16px', background: '#1e3a5f', color: '#93c5fd',
                border: '1px solid #3b82f6', borderRadius: '6px', cursor: 'pointer',
                fontSize: '13px', fontWeight: 500,
              }}
            >
              🔵 Real SAP
            </button>
            <button
              onClick={handleDiscoverSap}
              disabled={discovering}
              title="Fetch SAP $metadata, parse it, and index the source-schema RAG corpus (deterministic; no LLM)"
              style={{
                padding: '8px 16px', background: discovering ? '#334155' : '#1e3a5f', color: '#93c5fd',
                border: '1px solid #3b82f6', borderRadius: '6px', cursor: discovering ? 'not-allowed' : 'pointer',
                fontSize: '13px', fontWeight: 500,
              }}
            >
              {discovering ? '⏳ Discovering…' : '🔍 Discover SAP'}
            </button>
            <button
              onClick={addSource}
              style={{
                padding: '8px 16px', background: '#1e293b', color: '#3b82f6',
                border: '1px solid #3b82f6', borderRadius: '6px', cursor: 'pointer',
                fontSize: '13px', fontWeight: 500,
              }}
            >
              ➕ Add Source
            </button>
          </div>
        </div>
        {indexResult && (
          <div style={{
            padding: '8px 12px', background: '#064e3b', borderRadius: '6px',
            color: '#6ee7b7', fontSize: '12px', marginBottom: '12px',
          }}>
            {indexResult}
          </div>
        )}
        {sources.length === 0 ? (
          <div style={{
            textAlign: 'center', padding: '48px', background: '#1e293b',
            borderRadius: '8px', border: '1px dashed #334155',
          }}>
            <p style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '12px' }}>
              No data sources configured yet. Add SAP, MES, or custom API sources.
            </p>
            <p style={{ color: '#64748b', fontSize: '12px' }}>
              Hint: You'll need at least one connected source to proceed to mapping.
            </p>
          </div>
        ) : (
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))',
            gap: '12px',
          }}>
            {sources.map(source => (
              <SourceCard
                key={source.id || 'new'}
                source={source}
                onUpdate={updateSource}
                onTest={testSource}
                onRemove={removeSource}
              />
            ))}
          </div>
        )}
      </div>

      {discoveredSourceId && (
        <EntitySetBrowser
          sourceId={discoveredSourceId}
          selected={selectedEntitySets}
          onToggle={toggleEntitySet}
        />
      )}

      {/* Bottom bar */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '12px 0', borderTop: '1px solid #334155', marginTop: '16px',
      }}>
        <div style={{ fontSize: '13px', color: '#94a3b8' }}>
          {connectedCount} source{connectedCount !== 1 ? 's' : ''} connected
          {!canProceed && sources.length > 0 && ' — test at least one connection to proceed'}
        </div>
        <button
          onClick={handleNext}
          disabled={!canProceed}
          style={{
            padding: '10px 24px',
            background: canProceed ? '#3b82f6' : '#334155',
            color: canProceed ? '#fff' : '#64748b',
            border: 'none', borderRadius: '6px', cursor: canProceed ? 'pointer' : 'not-allowed',
            fontSize: '14px', fontWeight: 600,
          }}
        >
          Next → Mapping
        </button>
      </div>
    </div>
  );
}
