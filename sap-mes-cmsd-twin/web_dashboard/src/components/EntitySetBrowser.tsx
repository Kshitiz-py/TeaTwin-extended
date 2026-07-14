import { useState, useEffect } from 'react';
import { agentApi, SourceSchemaResponse, SampleResponse } from '../services/agentApi';

interface EntitySetBrowserProps {
  sourceId: string;
  selected: string[];
  onToggle: (entitySet: string) => void;
}

/**
 * Browses the discovered SAP OData $metadata schema (entity sets, properties with
 * sap:label / sap:unit, keys, nav properties) and offers a LOCAL-ONLY row preview.
 * Row data from the Sample button never leaves the browser — it is never sent to
 * the LLM or indexed in RAG.
 */
export default function EntitySetBrowser({ sourceId, selected, onToggle }: EntitySetBrowserProps) {
  const [schema, setSchema] = useState<SourceSchemaResponse | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [sample, setSample] = useState<SampleResponse | null>(null);
  const [loadingSample, setLoadingSample] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sourceId) return;
    setSchema(null);
    setError(null);
    agentApi.getSourceSchema(sourceId)
      .then(setSchema)
      .catch(e => setError(e.message));
  }, [sourceId]);

  const loadSample = async (entitySet: string) => {
    setLoadingSample(entitySet);
    setSample(null);
    try {
      setSample(await agentApi.sampleEntitySet(sourceId, entitySet, 3));
    } catch (e: any) {
      setError(e.message);
    }
    setLoadingSample(null);
  };

  if (error) return <div style={{ color: '#f87171', fontSize: 12, padding: 8 }}>{error}</div>;
  if (!schema) return <div style={{ color: '#94a3b8', fontSize: 12, padding: 8 }}>Loading schema…</div>;
  const types = schema.source_schema?.entity_types ?? [];
  if (!types.length) return <div style={{ color: '#94a3b8', fontSize: 12, padding: 8 }}>No schema found — run Discover first.</div>;

  return (
    <div style={{ border: '1px solid #334155', borderRadius: 8, background: '#0f172a', padding: 12, marginTop: 8 }}>
      <div style={{ color: '#cbd5e1', fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
        Discovered OData entity sets ({types.length}) — select the ones to expose for mapping
      </div>
      <div style={{ maxHeight: 320, overflowY: 'auto' }}>
        {types.map(et => {
          const isSel = selected.includes(et.entity_set_name);
          const isOpen = expanded === et.entity_set_name;
          return (
            <div key={et.name} style={{ borderBottom: '1px solid #1e293b', padding: '6px 0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input type="checkbox" checked={isSel} onChange={() => onToggle(et.entity_set_name)} />
                <span
                  style={{ color: '#e2e8f0', fontSize: 13, flex: 1, cursor: 'pointer' }}
                  onClick={() => setExpanded(isOpen ? null : et.entity_set_name)}
                >
                  {isOpen ? '▾' : '▸'} <b>{et.entity_set_name}</b>
                  <span style={{ color: '#64748b', marginLeft: 6, fontSize: 11 }}>
                    {et.sap_label ? `“${et.sap_label}” · ` : ''}{et.properties.length} props · {et.keys.length} keys · {et.navigation_properties.length} nav
                  </span>
                </span>
                <button
                  onClick={() => loadSample(et.entity_set_name)}
                  disabled={loadingSample === et.entity_set_name}
                  style={{ padding: '2px 8px', fontSize: 11, background: '#1e293b', color: '#93c5fd', border: '1px solid #334155', borderRadius: 4, cursor: 'pointer' }}
                >
                  {loadingSample === et.entity_set_name ? '…' : 'Sample 3'}
                </button>
              </div>
              {isOpen && (
                <div style={{ padding: '6px 12px', background: '#111827', borderRadius: 4, marginTop: 4 }}>
                  <div style={{ color: '#64748b', fontSize: 11, marginBottom: 4 }}>Keys: {et.keys.join(', ') || '—'}</div>
                  {et.properties.map(p => (
                    <div key={p.name} style={{ color: '#94a3b8', fontSize: 11, fontFamily: 'monospace' }}>
                      · {p.name}{' '}
                      <span style={{ color: '#64748b' }}>({p.type}{p.is_key ? ', KEY' : ''}{p.nullable ? '' : ', not-null'})</span>
                      {p.sap_label && <span style={{ color: '#93c5fd' }}> — “{p.sap_label}”</span>}
                      {p.sap_unit && <span style={{ color: '#fbbf24' }}> · sap:unit={p.sap_unit}</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
      {sample && (
        <div style={{ marginTop: 8, padding: 8, background: '#111827', borderRadius: 4 }}>
          <div style={{ color: '#fbbf24', fontSize: 11, marginBottom: 4 }}>
            ⚠ Row data preview — LOCAL ONLY, never sent to the LLM. ({sample.entity_set}, {sample.count} rows)
          </div>
          <pre style={{ color: '#94a3b8', fontSize: 11, maxHeight: 160, overflow: 'auto', margin: 0 }}>
            {JSON.stringify(sample.rows, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}