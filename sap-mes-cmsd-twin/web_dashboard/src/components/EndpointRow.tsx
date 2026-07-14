import { SourceData } from './SourceCard';

export interface EndpointRowData {
  source_id: string;
  endpoint: string;
  method: string;
  label: string;
}

export type PayloadStatus = 'none' | 'success' | 'error';

interface Props {
  data: EndpointRowData;
  sources: SourceData[];
  onChange: (data: EndpointRowData) => void;
  onRemove: () => void;
  onFire: () => void;
  loading: boolean;
  canRemove: boolean;
  approved: boolean;
  onApproveChange: (approved: boolean) => void;
  payloadStatus: PayloadStatus;
}

export default function EndpointRow({ data, sources, onChange, onRemove, onFire, loading, canRemove, approved, onApproveChange, payloadStatus }: Props) {
  const patch = (p: Partial<EndpointRowData>) => onChange({ ...data, ...p });
  const canFire = data.source_id && data.endpoint.trim() && !loading;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') onFire();
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
          value={data.source_id}
          onChange={e => patch({ source_id: e.target.value })}
          style={selectStyle}
        >
          {sources.length === 0 && <option value="">No sources</option>}
          {sources.map(s => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      </div>

      {/* Method */}
      <div style={{ minWidth: '90px' }}>
        <label style={labelStyle}>Method</label>
        <select
          value={data.method}
          onChange={e => patch({ method: e.target.value })}
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
          value={data.endpoint}
          onChange={e => patch({ endpoint: e.target.value })}
          onKeyDown={handleKeyDown}
          placeholder="/resources"
          style={inputStyle}
        />
      </div>

      {/* Label */}
      <div style={{ flex: 1, minWidth: '120px' }}>
        <label style={labelStyle}>Label (optional)</label>
        <input
          value={data.label}
          onChange={e => patch({ label: e.target.value })}
          onKeyDown={handleKeyDown}
          placeholder="e.g. SAP Resources"
          style={inputStyle}
        />
      </div>

      {/* Fire button */}
      <button
        onClick={onFire}
        disabled={!canFire}
        style={{
          padding: '8px 16px', borderRadius: '6px', border: 'none',
          background: canFire ? '#3b82f6' : '#334155',
          color: canFire ? '#fff' : '#64748b',
          cursor: canFire ? 'pointer' : 'not-allowed',
          fontSize: '13px', fontWeight: 600,
          display: 'flex', alignItems: 'center', gap: '6px',
          whiteSpace: 'nowrap', height: '36px',
        }}
      >
        {loading ? <><Spinner /> Fetching...</> : <>Fire</>}
      </button>

      {/* Approve checkbox */}
      <label
        title={
          payloadStatus === 'error' ? 'Cannot approve a failed fetch' :
          payloadStatus === 'none' ? 'Fire this endpoint first' :
          'Approve this payload for mapping'
        }
        style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          padding: '6px 10px', borderRadius: '6px',
          background: approved ? '#1a3a2a' : '#1e293b',
          border: approved ? '1px solid #22c55e' : '1px solid #334155',
          cursor: payloadStatus === 'success' ? 'pointer' : 'not-allowed',
          opacity: payloadStatus === 'success' ? 1 : 0.45,
          height: '36px', boxSizing: 'border-box',
          userSelect: 'none',
        }}
      >
        <input
          type="checkbox"
          checked={approved}
          onChange={e => onApproveChange(e.target.checked)}
          disabled={payloadStatus !== 'success'}
          style={{ accentColor: '#22c55e', cursor: payloadStatus === 'success' ? 'pointer' : 'not-allowed' }}
        />
        <span style={{ fontSize: '12px', color: approved ? '#bbf7d0' : '#94a3b8', fontWeight: 500 }}>
          Approve
        </span>
      </label>

      {/* Remove button */}
      <button
        onClick={onRemove}
        disabled={!canRemove}
        title={canRemove ? 'Remove this endpoint' : 'Cannot remove the last endpoint'}
        style={{
          padding: '6px 10px', borderRadius: '6px', border: '1px solid #475569',
          background: 'transparent', color: canRemove ? '#f87171' : '#475569',
          cursor: canRemove ? 'pointer' : 'not-allowed',
          fontSize: '16px', fontWeight: 700, height: '36px',
        }}
      >
        ✕
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
