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

function DebugBlock({ title, content, highlight }: { title: string; content: string; highlight?: boolean }) {
  const border = highlight ? '#3b82f6' : '#334155';
  return (
    <div style={{ background: '#0f172a', border: `1px solid ${border}`, borderRadius: 6, overflow: 'hidden' }}>
      <div style={{ padding: '6px 12px', background: '#1e293b', borderBottom: `1px solid ${border}`, fontSize: 11, color: highlight ? '#93c5fd' : '#94a3b8' }}>
        {title}
      </div>
      <pre style={{ padding: 12, margin: 0, overflow: 'auto', maxHeight: 400, color: '#e2e8f0', fontSize: 11, fontFamily: '"Fira Code","Cascadia Code","JetBrains Mono",monospace', lineHeight: 1.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
        {content}
      </pre>
    </div>
  );
}

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
  const [showDebug, setShowDebug] = useState(false);

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
          {rec.debug && (
            <div style={{ marginTop: 8 }}>
              <button
                onClick={() => setShowDebug(!showDebug)}
                style={{ padding: '6px 12px', background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#94a3b8', cursor: 'pointer', fontSize: 11, display: 'flex', alignItems: 'center', gap: 6, width: '100%' }}
              >
                <span>{showDebug ? '▲' : '▼'}</span>
                <span>🔍 View LLM prompt &amp; debug</span>
                <span style={{ marginLeft: 'auto', color: '#64748b', fontSize: 10 }}>{rec.debug.provider}/{rec.debug.model}</span>
              </button>
              {showDebug && (
                <div style={{ marginTop: 4, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ fontSize: 11, color: '#94a3b8', padding: '4px 8px' }}>
                    Model: <span style={{ color: '#a78bfa', fontFamily: 'monospace' }}>{rec.debug.provider}/{rec.debug.model}</span>
                  </div>
                  <DebugBlock title="System prompt" content={rec.debug.system_prompt} />
                  <DebugBlock title="User prompt (sent to LLM)" content={rec.debug.user_prompt} highlight />
                  <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 6, overflow: 'hidden' }}>
                    <div style={{ padding: '6px 12px', background: '#1e293b', borderBottom: '1px solid #334155', fontSize: 11, color: '#94a3b8' }}>
                      Phase-1 retrieval candidates (per CMSD field)
                    </div>
                    <div style={{ padding: 8 }}>
                      {Object.entries(rec.debug.candidates).map(([fname, hits]) => (
                        <div key={fname} style={{ marginBottom: 6 }}>
                          <div style={{ fontSize: 11, color: '#93c5fd', fontFamily: 'monospace' }}>
                            {fname} ({hits.length} hit{hits.length !== 1 ? 's' : ''})
                          </div>
                          {hits.map((h, i) => (
                            <div key={i} style={{ fontSize: 11, color: '#cbd5e1', paddingLeft: 12, fontFamily: 'monospace' }}>
                              <span style={{ color: '#fbbf24' }}>{h.score.toFixed(3)}</span>
                              {' '}{h.entity_set} — {h.content.slice(0, 200)}{h.content.length > 200 ? '…' : ''}
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  </div>
                  <DebugBlock title="Raw LLM response" content={rec.debug.raw_response} />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}