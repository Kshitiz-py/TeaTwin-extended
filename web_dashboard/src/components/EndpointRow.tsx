import { useState } from 'react';
import { SourceData } from './SourceCard';

export interface EndpointRowData {
  source_id: string;
  endpoint: string;
  method: string;
  label: string;
}

interface Props {
  sources: SourceData[];
  onFire: (data: EndpointRowData) => void;
  loading: boolean;
}

export default function EndpointRow({ sources, onFire, loading }: Props) {
  const [sourceId, setSourceId] = useState(sources[0]?.id || '');
  const [endpoint, setEndpoint] = useState('/resources');
  const [method, setMethod] = useState('GET');
  const [label, setLabel] = useState('');

  const canFire = sourceId && endpoint.trim() && !loading;

  const handleFire = () => {
    if (!canFire) return;
    onFire({
      source_id: sourceId,
      endpoint: endpoint.trim(),
      method,
      label: label.trim() || endpoint.trim(),
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleFire();
  };

  return (
    <div style={{
      display: 'flex', gap: '10px', alignItems: 'flex-end', flexWrap: 'wrap',
      padding: '16px', background: '#1e293b', borderRadius: '8px',
      border: '1px solid #334155',
    }}>
      {/* Source */}
      <div style={{ minWidth: '150px' }}>
        <label style={labelStyle}>Source</label>
        <select
          value={sourceId}
          onChange={e => setSourceId(e.target.value)}
          style={selectStyle}
        >
          {sources.length === 0 && (
            <option value="">No sources</option>
          )}
          {sources.map(s => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      </div>

      {/* Method */}
      <div style={{ minWidth: '90px' }}>
        <label style={labelStyle}>Method</label>
        <select
          value={method}
          onChange={e => setMethod(e.target.value)}
          style={selectStyle}
        >
          <option value="GET">GET</option>
          <option value="POST">POST</option>
        </select>
      </div>

      {/* Endpoint URL */}
      <div style={{ flex: 2, minWidth: '200px' }}>
        <label style={labelStyle}>Endpoint URL</label>
        <input
          value={endpoint}
          onChange={e => setEndpoint(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="/resources"
          style={inputStyle}
        />
      </div>

      {/* Label */}
      <div style={{ flex: 1, minWidth: '120px' }}>
        <label style={labelStyle}>Label (optional)</label>
        <input
          value={label}
          onChange={e => setLabel(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. SAP Resources"
          style={inputStyle}
        />
      </div>

      {/* Fire button */}
      <button
        onClick={handleFire}
        disabled={!canFire}
        style={{
          padding: '8px 20px', borderRadius: '6px', border: 'none',
          background: canFire ? '#3b82f6' : '#334155',
          color: canFire ? '#fff' : '#64748b',
          cursor: canFire ? 'pointer' : 'not-allowed',
          fontSize: '13px', fontWeight: 600,
          display: 'flex', alignItems: 'center', gap: '6px',
          whiteSpace: 'nowrap', height: '36px',
        }}
      >
        {loading ? (
          <>
            <Spinner />
            Fetching...
          </>
        ) : (
          <>Fire</>
        )}
      </button>
    </div>
  );
}

function Spinner() {
  return (
    <span style={{
      display: 'inline-block', width: '14px', height: '14px',
      border: '2px solid #475569', borderTopColor: '#93c5fd',
      borderRadius: '50%', animation: 'spin 0.6s linear infinite',
    }} />
  );
}

const labelStyle: React.CSSProperties = {
  fontSize: '11px', color: '#94a3b8', display: 'block',
  marginBottom: '4px', fontWeight: 500, textTransform: 'uppercase',
  letterSpacing: '0.5px',
};

const inputStyle: React.CSSProperties = {
  width: '100%', background: '#0f172a', border: '1px solid #334155',
  borderRadius: '4px', padding: '6px 10px', color: '#f1f5f9',
  fontSize: '13px', fontFamily: 'monospace', boxSizing: 'border-box',
  height: '36px',
};

const selectStyle: React.CSSProperties = {
  width: '100%', background: '#0f172a', border: '1px solid #334155',
  borderRadius: '4px', padding: '6px 10px', color: '#f1f5f9',
  fontSize: '13px', height: '36px', boxSizing: 'border-box',
};
