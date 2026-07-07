import { useState } from 'react';
import { agentApi, RecommendResponse } from '../services/agentApi';

interface PrefillEndpoint {
  sourceId: string;
  endpoint: string;
  method: string;
  label: string;
}

interface EndpointRecommendationProps {
  sourceId: string;
  cmsdEntity: string | null;
  onApprove: (endpoints: PrefillEndpoint[]) => void;
}

const CONF_COLOR: Record<string, string> = { high: '#6ee7b7', medium: '#fbbf24', low: '#f87171' };

/**
 * "Recommend endpoints" panel: calls the LLM-over-RAG recommender (metadata only)
 * to propose a covering set of OData endpoints for a CMSD entity, then lets the user
 * approve → pre-fill the endpoint list. Rendered inside the Guided Mapping wizard
 * after the CMSD entity is picked.
 */
export default function EndpointRecommendation({ sourceId, cmsdEntity, onApprove }: EndpointRecommendationProps) {
  const [rec, setRec] = useState<RecommendResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recommend = async () => {
    if (!cmsdEntity) return;
    setLoading(true); setError(null); setRec(null);
    try {
      setRec(await agentApi.recommendEndpoints(sourceId, cmsdEntity));
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  const approve = () => {
    if (!rec) return;
    const eps: PrefillEndpoint[] = (rec.covering_endpoints || []).map(ce => ({
      sourceId,
      endpoint: ce.endpoint,
      method: 'GET',
      label: ce.entity_set,
    }));
    onApprove(eps);
  };

  if (!cmsdEntity) return null;

  return (
    <div style={{ border: '1px solid #3b82f6', borderRadius: 8, background: '#0f172a', padding: 12, marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <div style={{ color: '#cbd5e1', fontSize: 13, fontWeight: 600 }}>
          🎯 Endpoint recommendation for <b>{cmsdEntity}</b>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={recommend}
            disabled={loading}
            style={{ padding: '6px 14px', fontSize: 12, background: '#1e3a5f', color: '#93c5fd', border: '1px solid #3b82f6', borderRadius: 6, cursor: 'pointer' }}
          >
            {loading ? '⏳ Recommending…' : 'Recommend endpoints'}
          </button>
          {rec && (
            <button
              onClick={approve}
              style={{ padding: '6px 14px', fontSize: 12, background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
            >
              Approve &amp; pre-fill →
            </button>
          )}
        </div>
      </div>
      {error && <div style={{ color: '#f87171', fontSize: 12 }}>{error}</div>}
      {rec && (
        <div>
          <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 6 }}>
            Covering endpoints: {rec.covering_endpoints.map(ce => `${ce.entity_set} (${ce.role})`).join(', ') || 'none'}
          </div>
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ color: '#64748b', textAlign: 'left' }}>
                <th style={{ padding: '4px 8px' }}>CMSD field</th><th></th>
                <th>entity_set.property</th><th>conf</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(rec.field_attribution || {}).map(([f, a]) => (
                <tr key={f} style={{ borderTop: '1px solid #1e293b' }}>
                  <td style={{ padding: '4px 8px', color: '#e2e8f0' }}>{f}</td>
                  <td style={{ color: '#64748b' }}>→</td>
                  <td style={{ color: '#93c5fd', fontFamily: 'monospace' }}>
                    {a.entity_set}.{a.property}
                    {a.unit_from_field && <span style={{ color: '#fbbf24' }}> · unit_from_field={a.unit_from_field.unit_path}</span>}
                  </td>
                  <td style={{ color: CONF_COLOR[a.confidence] || '#94a3b8' }}>{a.confidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {(rec.coverage_gaps || []).length > 0 && (
            <div style={{ color: '#f87171', fontSize: 12, marginTop: 6 }}>
              Coverage gaps: {rec.coverage_gaps.join(', ')}
            </div>
          )}
          {(rec.join_keys || []).length > 0 && (
            <div style={{ color: '#fbbf24', fontSize: 11, marginTop: 4 }}>
              Join keys: {rec.join_keys.map(j => `${j.from.entity_set}.${j.from.property}=${j.to.entity_set}.${j.to.property}`).join('; ')}
            </div>
          )}
          {rec.notes && <div style={{ color: '#64748b', fontSize: 11, marginTop: 4 }}>{rec.notes}</div>}
        </div>
      )}
    </div>
  );
}