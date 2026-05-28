import { useEffect, useState } from 'react';
import { api, ConnectionMetadata } from '../services/api';
import ConnectionIndicator from './ConnectionIndicator';

interface Resource {
  identifier: string;
  name: string;
  resource_type: string;
  current_status: string | null;
  availability: number | null;
  capacity: number | null;
  _connection?: ConnectionMetadata;
}

const statusBadgeStyle = (s: string | null): React.CSSProperties => {
  const colors: Record<string, string> = {
    busy: '#3b82f6', idle: '#22c55e', broken: '#ef4444', setup: '#f59e0b',
    paused: '#94a3b8', underMaintenance: '#a855f7', charging: '#06b6d4',
  };
  return {
    padding: '2px 10px', borderRadius: '10px', fontSize: '11px', fontWeight: 600,
    background: colors[s ?? ''] + '20', color: colors[s ?? ''] ?? '#64748b',
    border: `1px solid ${colors[s ?? ''] ?? '#64748b'}40`,
  };
};

const typeIcon = (t: string): string => {
  switch (t) {
    case 'machine': return '⚙️';
    case 'station': return '🖥️';
    case 'conveyor': return '➡️';
    case 'buffer': return '📦';
    case 'employee': return '👤';
    case 'transporter': return '🚛';
    case 'source': return '📥';
    case 'sink': return '📤';
    default: return '🔧';
  }
};

export default function ResourcePanel() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    api.getResources().then(setResources).catch(() => {});
    const interval = setInterval(() => {
      api.getResources().then(setResources).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const filtered = filter
    ? resources.filter(r => r.resource_type === filter || r.name.toLowerCase().includes(filter.toLowerCase()))
    : resources;

  const types = [...new Set(resources.map(r => r.resource_type))];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ color: '#f1f5f9' }}>Resources ({resources.length})</h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            style={{
              padding: '6px 12px', background: '#1e293b', color: '#e2e8f0',
              border: '1px solid #334155', borderRadius: '6px', fontSize: '13px',
            }}
          >
            <option value="">All Types</option>
            {types.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      </div>

      <div style={{ display: 'grid', gap: '8px' }}>
        {filtered.map(r => (
          <div key={r.identifier} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: '#1e293b', borderRadius: '8px', padding: '12px 16px',
            border: '1px solid #334155',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
              <span style={{ fontSize: '20px' }}>{typeIcon(r.resource_type)}</span>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <p style={{ fontSize: '14px', fontWeight: 600, color: '#f1f5f9', margin: 0 }}>{r.name}</p>
                  <ConnectionIndicator entity={r} />
                </div>
                <p style={{ fontSize: '11px', color: '#64748b', margin: '2px 0 0' }}>{r.identifier} · {r.resource_type}</p>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              {r.availability != null && (
                <div style={{ textAlign: 'right' }}>
                  <p style={{ fontSize: '11px', color: '#64748b' }}>Availability</p>
                  <p style={{ fontSize: '14px', fontWeight: 600, color: r.availability > 90 ? '#22c55e' : '#f59e0b' }}>
                    {r.availability.toFixed(1)}%
                  </p>
                </div>
              )}
              {r.capacity != null && (
                <div style={{ textAlign: 'right' }}>
                  <p style={{ fontSize: '11px', color: '#64748b' }}>Capacity</p>
                  <p style={{ fontSize: '14px', fontWeight: 600, color: '#e2e8f0' }}>{r.capacity}</p>
                </div>
              )}
              <span style={statusBadgeStyle(r.current_status)}>
                {r.current_status ?? 'unknown'}
              </span>
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <p style={{ color: '#64748b', textAlign: 'center', marginTop: '40px' }}>No resources match filter</p>
      )}
    </div>
  );
}