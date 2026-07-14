import { useEffect, useState } from 'react';

interface ResourceClass {
  identifier: string;
  name: string;
  resource_type: string;
  description?: string | null;
  hourly_rate?: { value: number; unit?: string } | null;
  size?: { width?: number; depth?: number; height?: number; unit?: string } | null;
  _connection?: any;
}

const typeIcon = (t: string): string => {
  switch (t) {
    case 'machine': return '';
    case 'station': return '';
    case 'conveyor': return '';
    case 'buffer': return '';
    case 'employee': return '';
    case 'transporter': return '';
    case 'source': return '';
    case 'sink': return '';
    default: return '';
  }
};

export default function ResourceClassPanel() {
  const [classes, setClasses] = useState<ResourceClass[]>([]);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    fetch('/api/cmsd/v1/digital-twin/resource-classes')
      .then(r => r.json())
      .then(setClasses)
      .catch(() => {});
    const interval = setInterval(() => {
      fetch('/api/cmsd/v1/digital-twin/resource-classes')
        .then(r => r.json())
        .then(setClasses)
        .catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const filtered = filter
    ? classes.filter(c => c.resource_type === filter || c.identifier.toLowerCase().includes(filter.toLowerCase()))
    : classes;

  const types = [...new Set(classes.map(c => c.resource_type))];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ color: '#f1f5f9' }}>Resource Classes ({classes.length})</h3>
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

      <div style={{ display: 'grid', gap: '8px' }}>
        {filtered.map(c => (
          <div key={c.identifier} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: '#1e293b', borderRadius: '8px', padding: '12px 16px',
            border: '1px solid #334155',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
              <span style={{ fontSize: '20px' }}>{typeIcon(c.resource_type)}</span>
              <div>
                <p style={{ fontSize: '14px', fontWeight: 600, color: '#f1f5f9', margin: 0 }}>{c.name || c.identifier}</p>
                <p style={{ fontSize: '11px', color: '#64748b', margin: '2px 0 0' }}>
                  <code style={{ color: '#a5b4fc', background: '#1e1b4b', padding: '1px 4px', borderRadius: '3px', fontFamily: 'monospace' }}>{c.identifier}</code>
                  {' '}· {c.resource_type}
                  {c.description && <span> · {c.description}</span>}
                </p>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              {c.hourly_rate && (
                <div style={{ textAlign: 'right' }}>
                  <p style={{ fontSize: '11px', color: '#64748b' }}>Rate</p>
                  <p style={{ fontSize: '14px', fontWeight: 600, color: '#22c55e' }}>
                    {typeof c.hourly_rate === 'object' ? c.hourly_rate.value : String(c.hourly_rate)}
                    {typeof c.hourly_rate === 'object' && c.hourly_rate.unit && (
                      <span style={{ fontSize: '10px', color: '#64748b' }}> {c.hourly_rate.unit}</span>
                    )}
                  </p>
                </div>
              )}
              {c.size && (
                <div style={{ textAlign: 'right' }}>
                  <p style={{ fontSize: '11px', color: '#64748b' }}>Size (mm)</p>
                  <p style={{ fontSize: '11px', fontWeight: 500, color: '#e2e8f0' }}>
                    {c.size.width ?? '—'} × {c.size.depth ?? '—'} × {c.size.height ?? '—'}
                  </p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <p style={{ color: '#64748b', textAlign: 'center', marginTop: '40px' }}>No resource classes match filter</p>
      )}
    </div>
  );
}
