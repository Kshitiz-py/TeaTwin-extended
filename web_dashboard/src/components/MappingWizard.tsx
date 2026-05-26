import { useState, useEffect } from 'react';
import EndpointRow, { EndpointRowData } from './EndpointRow';
import PayloadViewer from './PayloadViewer';
import { agentApi, FetchedPayload } from '../services/agentApi';
import { SourceData } from './SourceCard';

export default function MappingWizard() {
  const [sources, setSources] = useState<SourceData[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [fetchLoading, setFetchLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payloads, setPayloads] = useState<FetchedPayload[]>([]);

  useEffect(() => {
    agentApi.getSources()
      .then(data => setSources(data.sources || []))
      .catch(() => setError('Failed to load data sources.'))
      .finally(() => setSourcesLoading(false));
  }, []);

  const handleFire = async (data: EndpointRowData) => {
    setFetchLoading(true);
    setError(null);
    try {
      const result = await agentApi.fetchEndpoints([{
        source_id: data.source_id,
        endpoint: data.endpoint,
        method: data.method,
        label: data.label,
      }]);
      setPayloads(result.payloads);
    } catch (e: any) {
      setError(e.message || 'Fetch failed');
      setPayloads([]);
    } finally {
      setFetchLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      <style>{'@keyframes spin { to { transform: rotate(360deg); } }'}</style>

      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ color: '#f1f5f9', margin: '0 0 4px', fontSize: '20px' }}>
          API Explorer
        </h2>
        <p style={{ color: '#94a3b8', margin: 0, fontSize: '13px' }}>
          Select a source, enter an endpoint, and fire to inspect the raw JSON response.
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div style={{
          padding: '10px 16px', background: '#7f1d1d', borderRadius: '8px',
          border: '1px solid #ef4444', color: '#fca5a5', fontSize: '13px',
          marginBottom: '14px',
        }}>
          {error}
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
        <EndpointRow
          sources={sources}
          onFire={handleFire}
          loading={fetchLoading}
        />
      )}

      {/* Payload viewers */}
      {payloads.map((p, i) => (
        <PayloadViewer key={i} payload={p} />
      ))}
    </div>
  );
}
