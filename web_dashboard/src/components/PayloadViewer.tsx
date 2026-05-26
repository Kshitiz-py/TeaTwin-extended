import { useState } from 'react';
import { FetchedPayload } from '../services/agentApi';

interface Props {
  payload: FetchedPayload;
}

const COLORS: Record<string, string> = {
  string: '#4ade80',
  number: '#60a5fa',
  boolean: '#fbbf24',
  null: '#94a3b8',
  key: '#a78bfa',
  bracket: '#e2e8f0',
  colon: '#64748b',
};

function isTruncated(raw: any): boolean {
  return raw && typeof raw === 'object' && raw._truncated === true;
}

export default function PayloadViewer({ payload }: Props) {
  const [collapsed, setCollapsed] = useState(false);

  if (payload.status === 'error') {
    return (
      <div style={{
        marginTop: '12px', padding: '12px 16px', background: '#7f1d1d',
        borderRadius: '8px', border: '1px solid #ef4444', color: '#fca5a5',
        fontSize: '13px',
      }}>
        <strong>Error</strong>
        {payload.url && <span style={{ marginLeft: '8px', opacity: 0.8 }}>{payload.url}</span>}
        {payload.status_code && (
          <span style={{ marginLeft: '8px', opacity: 0.8 }}>HTTP {payload.status_code}</span>
        )}
        <pre style={{
          margin: '8px 0 0', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
          fontSize: '12px', color: '#fca5a5', opacity: 0.9,
        }}>
          {JSON.stringify(payload.raw_payload, null, 2)}
        </pre>
      </div>
    );
  }

  const truncated = isTruncated(payload.raw_payload);
  const displayData = truncated ? payload.raw_payload._preview : payload.raw_payload;
  const fullSize = truncated ? payload.raw_payload._full_size_bytes : null;

  return (
    <div style={{
      marginTop: '12px', background: '#0f172a', borderRadius: '8px',
      border: '1px solid #334155', overflow: 'hidden',
    }}>
      {/* Header bar */}
      <div style={{
        padding: '8px 14px', background: '#1e293b', borderBottom: '1px solid #334155',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        fontSize: '12px', flexWrap: 'wrap', gap: '6px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontFamily: 'monospace', color: '#a78bfa', fontSize: '12px' }}>
            {payload.label || payload.endpoint}
          </span>
          {payload.status_code && (
            <span style={{
              padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
              background: payload.status_code < 400 ? '#064e3b' : '#7f1d1d',
              color: payload.status_code < 400 ? '#4ade80' : '#fca5a5',
            }}>
              HTTP {payload.status_code}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ color: '#94a3b8' }}>
            {formatBytes(payload.size_bytes)}
          </span>
          <button
            onClick={() => setCollapsed(c => !c)}
            style={{
              padding: '2px 8px', borderRadius: '4px', border: '1px solid #475569',
              background: '#0f172a', color: '#94a3b8', cursor: 'pointer', fontSize: '11px',
            }}
          >
            {collapsed ? 'Expand' : 'Collapse'} All
          </button>
        </div>
      </div>

      {/* Truncation banner */}
      {truncated && (
        <div style={{
          padding: '6px 14px', background: '#78350f', color: '#fbbf24',
          fontSize: '11px', borderBottom: '1px solid #334155',
          display: 'flex', alignItems: 'center', gap: '6px',
        }}>
          <span>⚠</span>
          Payload truncated at 5,000 bytes. Full size: {fullSize?.toLocaleString()} bytes.
        </div>
      )}

      {/* JSON content */}
      {!collapsed && (
        <div style={{ padding: '12px', overflow: 'auto', maxHeight: '500px' }}>
          <pre style={{
            margin: 0, fontFamily: '"Fira Code", "Cascadia Code", "JetBrains Mono", monospace',
            fontSize: '12px', lineHeight: '1.6', color: '#e2e8f0', whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}>
            <JsonTree value={displayData} depth={0} initialCollapsed={false} />
          </pre>
        </div>
      )}
    </div>
  );
}

// ─── JSON Tree Renderer ─────────────────────────────────────

interface JsonTreeProps {
  value: any;
  depth: number;
  initialCollapsed?: boolean;
}

function JsonTree({ value, depth, initialCollapsed }: JsonTreeProps) {
  if (value === null) return <span style={{ color: COLORS.null }}>null</span>;
  if (value === undefined) return <span style={{ color: COLORS.null }}>undefined</span>;
  if (typeof value === 'boolean') return <span style={{ color: COLORS.boolean }}>{String(value)}</span>;
  if (typeof value === 'number') return <span style={{ color: COLORS.number }}>{String(value)}</span>;
  if (typeof value === 'string') {
    // If it's already a JSON string (truncated preview), just show it
    if (value.length > 200 && depth === 0) {
      try { JSON.parse(value); return <span style={{ color: COLORS.string, whiteSpace: 'pre-wrap' }}>{value}</span>; } catch {}
    }
    return <span style={{ color: COLORS.string }}>"{value}"</span>;
  }

  if (Array.isArray(value)) {
    return <JsonCollection value={value} depth={depth} isArray initialCollapsed={initialCollapsed} />;
  }

  if (typeof value === 'object') {
    return <JsonCollection value={value} depth={depth} isArray={false} initialCollapsed={initialCollapsed} />;
  }

  return <span>{String(value)}</span>;
}

// ─── Collapsible JSON Collection ────────────────────────────

function JsonCollection({ value, depth, isArray, initialCollapsed }: {
  value: any;
  depth: number;
  isArray: boolean;
  initialCollapsed?: boolean;
}) {
  const keys = isArray ? null : Object.keys(value);
  const entries = isArray ? value : keys!;
  const count = isArray ? value.length : keys!.length;
  const [collapsed, setCollapsed] = useState(initialCollapsed ?? depth >= 3);

  const openBracket = isArray ? '[' : '{';
  const closeBracket = isArray ? ']' : '}';

  if (count === 0) {
    return <span style={{ color: COLORS.bracket }}>{openBracket}{closeBracket}</span>;
  }

  const toggle = () => setCollapsed(c => !c);

  if (collapsed) {
    const preview = isArray
      ? `${openBracket} ${count} item${count !== 1 ? 's' : ''} ${closeBracket}`
      : `${openBracket} ${count} key${count !== 1 ? 's' : ''} ${closeBracket}`;
    return (
      <span
        onClick={toggle}
        style={{ color: COLORS.bracket, cursor: 'pointer' }}
        title="Click to expand"
      >
        {preview}
      </span>
    );
  }

  const indent = '  '.repeat(depth + 1);
  const closeIndent = '  '.repeat(depth);

  return (
    <>
      <span
        onClick={toggle}
        style={{ color: COLORS.bracket, cursor: 'pointer' }}
        title="Click to collapse"
      >
        {openBracket}
      </span>
      {'\n'}
      {isArray
        ? entries.map((item: any, i: number) => (
            <span key={i}>
              {indent && <span>{indent}</span>}
              <JsonTree value={item} depth={depth + 1} />
              {i < entries.length - 1 && <span style={{ color: COLORS.colon }}>,</span>}
              {'\n'}
            </span>
          ))
        : keys!.map((key: string) => (
            <span key={key}>
              {indent && <span>{indent}</span>}
              <span style={{ color: COLORS.key }}>"{key}"</span>
              <span style={{ color: COLORS.colon }}>: </span>
              <JsonTree value={value[key]} depth={depth + 1} />
              <span style={{ color: COLORS.colon }}>,</span>
              {'\n'}
            </span>
          ))
      }
      <span style={{ color: COLORS.bracket }}>{closeIndent}{closeBracket}</span>
    </>
  );
}

// ─── Helpers ────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
