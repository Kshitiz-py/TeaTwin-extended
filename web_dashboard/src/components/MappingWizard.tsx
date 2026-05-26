import { useState, useEffect } from 'react';
import EndpointRow, { EndpointRowData } from './EndpointRow';
import PayloadViewer from './PayloadViewer';
import { agentApi, FetchedPayload } from '../services/agentApi';
import { SourceData } from './SourceCard';

function defaultEndpoint(sources: SourceData[]): EndpointRowData {
  return {
    source_id: sources[0]?.id || '',
    endpoint: '/resources',
    method: 'GET',
    label: '',
  };
}

export default function MappingWizard() {
  const [sources, setSources] = useState<SourceData[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [endpoints, setEndpoints] = useState<EndpointRowData[]>([]);
  const [payloads, setPayloads] = useState<(FetchedPayload | null)[]>([]);
  const [loading, setLoading] = useState<Set<number>>(new Set()); // which indices are loading
  const [fireAllLoading, setFireAllLoading] = useState(false);

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

  // ── Add / Remove ──────────────────────────────────────────

  const addEndpoint = () => {
    setEndpoints(prev => [...prev, defaultEndpoint(sources)]);
    setPayloads(prev => [...prev, null]);
  };

  const removeEndpoint = (i: number) => {
    if (endpoints.length <= 1) return;
    setEndpoints(prev => prev.filter((_, idx) => idx !== i));
    setPayloads(prev => prev.filter((_, idx) => idx !== i));
  };

  const updateEndpoint = (i: number, data: EndpointRowData) => {
    setEndpoints(prev => prev.map((ep, idx) => idx === i ? data : ep));
  };

  // ── Fire single ───────────────────────────────────────────

  const fireSingle = async (i: number) => {
    const ep = endpoints[i];
    if (!ep) return;

    setLoading(prev => new Set(prev).add(i));
    try {
      const result = await agentApi.fetchEndpoints([{
        source_id: ep.source_id,
        endpoint: ep.endpoint,
        method: ep.method,
        label: ep.label || ep.endpoint,
      }]);
      setPayloads(prev => prev.map((p, idx) => idx === i ? result.payloads[0] : p));
    } catch (e: any) {
      setPayloads(prev => prev.map((p, idx) => idx === i ? {
        endpoint: ep.endpoint,
        source_id: ep.source_id,
        label: ep.label || ep.endpoint,
        url: '',
        status: 'error' as const,
        error_message: e.message || 'Fetch failed',
        status_code: null,
        size_bytes: 0,
        raw_payload: null,
      } : p));
    } finally {
      setLoading(prev => { const next = new Set(prev); next.delete(i); return next; });
    }
  };

  // ── Fire all ──────────────────────────────────────────────

  const fireAll = async () => {
    setFireAllLoading(true);
    try {
      const result = await agentApi.fetchEndpoints(
        endpoints.map(ep => ({
          source_id: ep.source_id,
          endpoint: ep.endpoint,
          method: ep.method,
          label: ep.label || ep.endpoint,
        }))
      );
      // Map results back by index (response order matches request order)
      setPayloads(result.payloads);
    } catch (e: any) {
      // If the whole batch call failed, mark all as error
      setPayloads(endpoints.map(ep => ({
        endpoint: ep.endpoint,
        source_id: ep.source_id,
        label: ep.label || ep.endpoint,
        url: '',
        status: 'error' as const,
        error_message: e.message || 'Fire All failed',
        status_code: null,
        size_bytes: 0,
        raw_payload: null,
      })));
    } finally {
      setFireAllLoading(false);
    }
  };

  const isLoadingAny = loading.size > 0 || fireAllLoading;

  // ── Render ────────────────────────────────────────────────

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto' }}>
      <style>{'@keyframes spin { to { transform: rotate(360deg); } }'}</style>

      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ color: '#f1f5f9', margin: '0 0 4px', fontSize: '20px' }}>
          API Explorer
        </h2>
        <p style={{ color: '#94a3b8', margin: 0, fontSize: '13px' }}>
          Add endpoints, fire individually or all at once. Partial success is supported.
        </p>
      </div>

      {/* Error banner */}
      {sourceError && (
        <div style={{
          padding: '10px 16px', background: '#7f1d1d', borderRadius: '8px',
          border: '1px solid #ef4444', color: '#fca5a5', fontSize: '13px',
          marginBottom: '14px',
        }}>
          {sourceError}
        </div>
      )}

      {sourcesLoading ? (
        <div style={{
          padding: '24px', textAlign: 'center', color: '#94a3b8', fontSize: '13px',
        }}>
          Loading sources...
        </div>
      ) : sources.length === 0 ? (
        <div style={{
          padding: '32px', textAlign: 'center', background: '#1e293b',
          borderRadius: '8px', border: '1px dashed #475569', color: '#94a3b8',
          fontSize: '13px',
        }}>
          No data sources configured. Use the <strong>Connect Sources</strong> step first.
        </div>
      ) : (
        <>
          {/* Empty state */}
          {endpoints.length === 0 && (
            <div style={{
              padding: '32px', textAlign: 'center', background: '#1e293b',
              borderRadius: '8px', border: '1px dashed #475569', color: '#94a3b8',
              fontSize: '13px', marginBottom: '12px',
            }}>
              Add at least one endpoint to begin.
            </div>
          )}

          {/* Endpoint rows */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {endpoints.map((ep, i) => (
              <div key={i}>
                <EndpointRow
                  data={ep}
                  sources={sources}
                  onChange={(d) => updateEndpoint(i, d)}
                  onRemove={() => removeEndpoint(i)}
                  onFire={() => fireSingle(i)}
                  loading={loading.has(i)}
                  canRemove={endpoints.length > 1}
                />
                {payloads[i] && (
                  <PayloadViewer
                    payload={payloads[i]}
                    onRetry={() => fireSingle(i)}
                  />
                )}
              </div>
            ))}
          </div>

          {/* Action buttons */}
          <div style={{
            display: 'flex', gap: '10px', marginTop: '14px',
            paddingTop: '14px', borderTop: '1px solid #334155',
            alignItems: 'center',
          }}>
            <button
              onClick={addEndpoint}
              disabled={isLoadingAny}
              style={{
                padding: '8px 18px', borderRadius: '6px',
                border: '1px dashed #475569', background: '#1e3a5f',
                color: isLoadingAny ? '#64748b' : '#93c5fd',
                cursor: isLoadingAny ? 'not-allowed' : 'pointer',
                fontSize: '13px', fontWeight: 600,
              }}
            >
              + Add Endpoint
            </button>

            <button
              onClick={fireAll}
              disabled={endpoints.length === 0 || isLoadingAny}
              style={{
                padding: '10px 28px', borderRadius: '6px', border: 'none',
                background: endpoints.length === 0 || isLoadingAny ? '#334155' : '#7c3aed',
                color: endpoints.length === 0 || isLoadingAny ? '#64748b' : '#fff',
                cursor: endpoints.length === 0 || isLoadingAny ? 'not-allowed' : 'pointer',
                fontSize: '14px', fontWeight: 700,
                display: 'flex', alignItems: 'center', gap: '8px',
              }}
            >
              {fireAllLoading ? (
                <>⏳ Fetching {endpoints.length} endpoint{endpoints.length !== 1 ? 's' : ''}...</>
              ) : (
                <>🚀 Fire All ({endpoints.length})</>
              )}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
