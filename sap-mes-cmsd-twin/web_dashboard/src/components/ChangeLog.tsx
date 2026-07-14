import { useState } from 'react';

interface ChangeEvent {
  entity_type: string;
  entity_identifier: string;
  entity_name: string;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  event_type: string;
  timestamp: string;
}

interface Props {
  events: ChangeEvent[];
}

const eventColor = (t: string): string => {
  switch (t) {
    case 'created': return '#22c55e';
    case 'deleted': return '#ef4444';
    case 'updated': return '#3b82f6';
    default: return '#94a3b8';
  }
};

export default function ChangeLog({ events }: Props) {
  const [filter, setFilter] = useState('');

  const filtered = filter
    ? events.filter(e => e.entity_type === filter || e.event_type === filter)
    : events;

  const entityTypes = [...new Set(events.map(e => e.entity_type))];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ color: '#f1f5f9' }}>Change Events ({events.length})</h3>
        <select
          value={filter}
          onChange={e => setFilter(e.target.value)}
          style={{
            padding: '6px 12px', background: '#1e293b', color: '#e2e8f0',
            border: '1px solid #334155', borderRadius: '6px', fontSize: '13px',
          }}
        >
          <option value="">All</option>
          {entityTypes.map(t => <option key={t} value={t}>{t}</option>)}
          <option value="created">created</option>
          <option value="updated">updated</option>
          <option value="deleted">deleted</option>
        </select>
      </div>

      <div style={{ display: 'grid', gap: '6px', maxHeight: '600px', overflowY: 'auto' }}>
        {filtered.map((ev, i) => (
          <div key={`${ev.timestamp}-${i}`} style={{
            display: 'flex', alignItems: 'center', gap: '12px',
            background: '#1e293b', borderRadius: '6px', padding: '10px 14px',
            border: '1px solid #334155', fontSize: '13px',
          }}>
            <span style={{
              padding: '2px 8px', borderRadius: '8px', fontSize: '10px', fontWeight: 700,
              background: eventColor(ev.event_type) + '20', color: eventColor(ev.event_type),
              border: `1px solid ${eventColor(ev.event_type)}40`, minWidth: '60px', textAlign: 'center',
            }}>
              {ev.event_type}
            </span>
            <span style={{ color: '#f1f5f9', fontWeight: 600, minWidth: '70px' }}>{ev.entity_type}</span>
            <span style={{ color: '#cbd5e1', minWidth: '100px' }}>{ev.entity_name}</span>
            <span style={{ color: '#64748b' }}>{ev.field_name}</span>
            <div style={{ display: 'flex', gap: '6px', flex: 1, justifyContent: 'flex-end' }}>
              {ev.old_value != null && (
                <span style={{
                  padding: '1px 8px', borderRadius: '4px', fontSize: '11px',
                  background: '#7f1d1d', color: '#fca5a5', maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {ev.old_value}
                </span>
              )}
              {ev.new_value != null && (
                <span style={{
                  padding: '1px 8px', borderRadius: '4px', fontSize: '11px',
                  background: '#064e3b', color: '#6ee7b7', maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {ev.new_value}
                </span>
              )}
            </div>
            <span style={{ fontSize: '10px', color: '#475569', minWidth: '70px', textAlign: 'right' }}>
              {new Date(ev.timestamp).toLocaleTimeString()}
            </span>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <p style={{ color: '#64748b', textAlign: 'center', marginTop: '40px' }}>
          {events.length === 0 ? 'Waiting for change events from the digital twin...' : 'No events match filter'}
        </p>
      )}
    </div>
  );
}