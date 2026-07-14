import { useState } from 'react';

export interface SourceData {
  id: string;
  name: string;
  base_url: string;
  auth_type: string;
  username?: string;
  password?: string;
  token?: string;
  api_key?: string;
  api_key_header?: string;
  client_id?: string;
  client_secret?: string;
  extra_headers?: Record<string, string>;
  status?: string;
  last_tested?: string;
  latency_ms?: number;
}

interface SourceCardProps {
  source: SourceData;
  onUpdate: (source: SourceData) => void;
  onTest: (sourceId: string) => void;
  onRemove: (sourceId: string) => void;
}

const AUTH_TYPES = ['none', 'basic', 'bearer', 'oauth2', 'api_key', 'mtls'];

const icon = (name: string) => {
  const n = name.toLowerCase();
  if (n.includes('sap')) return '🔵';
  if (n.includes('mes')) return '🟢';
  return '⚪';
};

const statusColor = (status?: string) => {
  switch (status) {
    case 'connected': return '#22c55e';
    case 'testing': return '#f59e0b';
    case 'failed': return '#ef4444';
    default: return '#64748b';
  }
};

const statusLabel = (status?: string) => {
  switch (status) {
    case 'connected': return '✅ Connected';
    case 'testing': return '⏳ Testing…';
    case 'failed': return '❌ Failed';
    default: return '⚪ Configured';
  }
};

export default function SourceCard({ source, onUpdate, onTest, onRemove }: SourceCardProps) {
  const [headers, setHeaders] = useState<[string, string][]>(
    source.extra_headers ? Object.entries(source.extra_headers) : []
  );

  const update = (patch: Partial<SourceData>) => {
    const updated = { ...source, ...patch };
    if (patch.extra_headers !== undefined) {
      updated.extra_headers = Object.fromEntries(headers.filter(([k]) => k.trim()));
    }
    onUpdate(updated);
  };

  const addHeader = () => setHeaders(prev => [...prev, ['', '']]);
  const removeHeader = (i: number) => {
    const next = headers.filter((_, idx) => idx !== i);
    setHeaders(next);
    update({ extra_headers: Object.fromEntries(next.filter(([k]) => k.trim())) });
  };
  const setHeader = (i: number, key: string, value: string) => {
    const next = headers.map((h, idx) => (idx === i ? [key, value] : h));
    setHeaders(next);
    update({ extra_headers: Object.fromEntries(next.filter(([k]) => k.trim())) });
  };

  return (
    <div style={{ background: '#1e293b', borderRadius: '8px', padding: '16px', border: '1px solid #334155', position: 'relative' }}>
      {/* Remove button */}
      <button
        onClick={() => onRemove(source.id)}
        style={{ position: 'absolute', top: '8px', right: '8px', background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '18px' }}
      >×</button>

      {/* Name + icon */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '12px' }}>
        <span style={{ fontSize: '20px' }}>{icon(source.name)}</span>
        <input
          value={source.name}
          onChange={e => update({ name: e.target.value })}
          style={{ flex: 1, background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '6px 8px', color: '#f1f5f9', fontSize: '14px', fontWeight: 600 }}
        />
      </div>

      {/* Base URL */}
      <label style={{ fontSize: '11px', color: '#94a3b8', display: 'block', marginBottom: '2px' }}>Base URL</label>
      <input
        value={source.base_url}
        onChange={e => update({ base_url: e.target.value })}
        placeholder="https://..."
        style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '6px 8px', color: '#f1f5f9', fontSize: '13px', marginBottom: '10px', boxSizing: 'border-box' }}
      />

      {/* Auth Type */}
      <label style={{ fontSize: '11px', color: '#94a3b8', display: 'block', marginBottom: '2px' }}>Auth Type</label>
      <select
        value={source.auth_type}
        onChange={e => update({ auth_type: e.target.value })}
        style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '6px 8px', color: '#f1f5f9', fontSize: '13px', marginBottom: '10px' }}
      >
        {AUTH_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
      </select>

      {/* Conditional auth fields */}
      {(source.auth_type === 'basic') && (
        <>
          <input value={source.username || ''} onChange={e => update({ username: e.target.value })} placeholder="Username" style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '6px 8px', color: '#f1f5f9', fontSize: '13px', marginBottom: '6px', boxSizing: 'border-box' }} />
          <input value={source.password || ''} onChange={e => update({ password: e.target.value })} placeholder="Password" type="password" style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '6px 8px', color: '#f1f5f9', fontSize: '13px', marginBottom: '10px', boxSizing: 'border-box' }} />
        </>
      )}
      {source.auth_type === 'bearer' && (
        <input value={source.token || ''} onChange={e => update({ token: e.target.value })} placeholder="Bearer Token" style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '6px 8px', color: '#f1f5f9', fontSize: '13px', marginBottom: '10px', boxSizing: 'border-box' }} />
      )}
      {source.auth_type === 'api_key' && (
        <>
          <input value={source.api_key_header || 'X-API-Key'} onChange={e => update({ api_key_header: e.target.value })} placeholder="Header name" style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '6px 8px', color: '#f1f5f9', fontSize: '13px', marginBottom: '6px', boxSizing: 'border-box' }} />
          <input value={source.api_key || ''} onChange={e => update({ api_key: e.target.value })} placeholder="API Key" style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '6px 8px', color: '#f1f5f9', fontSize: '13px', marginBottom: '10px', boxSizing: 'border-box' }} />
        </>
      )}
      {source.auth_type === 'oauth2' && (
        <>
          <input value={source.client_id || ''} onChange={e => update({ client_id: e.target.value })} placeholder="Client ID" style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '6px 8px', color: '#f1f5f9', fontSize: '13px', marginBottom: '6px', boxSizing: 'border-box' }} />
          <input value={source.client_secret || ''} onChange={e => update({ client_secret: e.target.value })} placeholder="Client Secret" type="password" style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '6px 8px', color: '#f1f5f9', fontSize: '13px', marginBottom: '10px', boxSizing: 'border-box' }} />
        </>
      )}

      {/* Extra headers */}
      <div style={{ marginBottom: '10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
          <span style={{ fontSize: '11px', color: '#94a3b8' }}>Extra Headers</span>
          <button onClick={addHeader} style={{ background: 'none', border: 'none', color: '#3b82f6', cursor: 'pointer', fontSize: '12px' }}>+ Add</button>
        </div>
        {headers.map(([k, v], i) => (
          <div key={i} style={{ display: 'flex', gap: '4px', marginBottom: '4px' }}>
            <input value={k} onChange={e => setHeader(i, e.target.value, v)} placeholder="Key" style={{ flex: 1, background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '4px 6px', color: '#f1f5f9', fontSize: '12px' }} />
            <input value={v} onChange={e => setHeader(i, k, e.target.value)} placeholder="Value" style={{ flex: 1, background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '4px 6px', color: '#f1f5f9', fontSize: '12px' }} />
            <button onClick={() => removeHeader(i)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '14px' }}>×</button>
          </div>
        ))}
      </div>

      {/* Test + Status */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
        <button
          onClick={() => onTest(source.id)}
          disabled={source.status === 'testing'}
          style={{ padding: '6px 14px', borderRadius: '6px', border: '1px solid #3b82f6', background: source.status === 'testing' ? '#334155' : '#1e293b', color: source.status === 'testing' ? '#64748b' : '#3b82f6', cursor: source.status === 'testing' ? 'not-allowed' : 'pointer', fontSize: '13px' }}
        >
          {source.status === 'testing' ? 'Testing…' : 'Test Connection'}
        </button>
        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '12px', color: statusColor(source.status), fontWeight: 500 }}>
            {statusLabel(source.status)}
          </span>
          {source.latency_ms !== undefined && source.status === 'connected' && (
            <span style={{ fontSize: '10px', color: '#94a3b8', marginLeft: '6px' }}>{source.latency_ms}ms</span>
          )}
          {source.last_tested && (
            <div style={{ fontSize: '10px', color: '#64748b', marginTop: '2px' }}>
              {new Date(source.last_tested).toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
