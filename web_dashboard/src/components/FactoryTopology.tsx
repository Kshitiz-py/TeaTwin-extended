import { useEffect, useState } from 'react';
import { api } from '../services/api';

interface Placement {
  resource_identifier: string;
  resource_name: string;
  x: number;
  y: number;
  z: number;
}

interface ResourceStatus {
  identifier: string;
  name: string;
  resource_type: string;
  current_status: string | null;
  availability: number | null;
}

interface LayoutData {
  identifier: string;
  name: string;
  placements: Placement[];
}

interface ConnectionData {
  identifier: string;
  name: string | null;
  from_resource: string | null;
  to_resource: string | null;
  connection_type: string | null;
}

interface Props {
  events: any[];
}

const statusColor = (s: string | null): string => {
  if (!s) return '#64748b';
  switch (s) {
    case 'busy': return '#3b82f6';
    case 'idle': return '#22c55e';
    case 'broken': return '#ef4444';
    case 'setup': return '#f59e0b';
    case 'paused': return '#94a3b8';
    case 'underMaintenance': return '#a855f7';
    default: return '#64748b';
  }
};

const connTypeColor = (t: string | null): string => {
  switch (t) {
    case 'conveyor': return '#06b6d4';
    case 'path': return '#8b5cf6';
    default: return '#475569';
  }
};

export default function FactoryTopology({ events }: Props) {
  const [resources, setResources] = useState<ResourceStatus[]>([]);
  const [layout, setLayout] = useState<LayoutData | null>(null);
  const [connections, setConnections] = useState<ConnectionData[]>([]);
  const [statusMap, setStatusMap] = useState<Record<string, string | null>>({});
  const [showConnections, setShowConnections] = useState(true);

  useEffect(() => {
    api.getResources().then((data: ResourceStatus[]) => {
      setResources(data);
      const map: Record<string, string | null> = {};
      data.forEach((r: ResourceStatus) => { map[r.identifier] = r.current_status; });
      setStatusMap(map);
    }).catch(() => {});

    api.getLayout().then((data: LayoutData) => { setLayout(data); }).catch(() => {});

    api.getConnections().then((data: ConnectionData[]) => { setConnections(data); }).catch(() => {});
  }, []);

  useEffect(() => {
    if (events.length === 0) return;
    const latest = events[0];
    if (latest.entity_type === 'resource' && latest.field_name === 'current_status') {
      setStatusMap(prev => ({ ...prev, [latest.entity_identifier]: latest.new_value }));
    }
  }, [events]);

  const positionMap: Record<string, { x: number; y: number }> = {};
  if (layout?.placements) {
    for (const p of layout.placements) {
      positionMap[p.resource_identifier] = { x: p.x, y: p.y };
    }
  }

  const positions = Object.values(positionMap);
  const minX = positions.length > 0 ? Math.min(...positions.map(p => p.x)) : 0;
  const maxX = positions.length > 0 ? Math.max(...positions.map(p => p.x)) : 30;
  const minY = positions.length > 0 ? Math.min(...positions.map(p => p.y)) : 0;
  const maxY = positions.length > 0 ? Math.max(...positions.map(p => p.y)) : 30;
  const rangeX = maxX - minX || 30;
  const rangeY = maxY - minY || 30;
  const padding = 3;

  // Filter connections where both endpoints have placement data
  const visibleConnections = connections.filter(
    c => c.from_resource && c.to_resource && positionMap[c.from_resource] && positionMap[c.to_resource]
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ color: '#f1f5f9' }}>
          Factory Floor Layout
          {layout && <span style={{ fontSize: '13px', fontWeight: 400, color: '#64748b', marginLeft: '8px' }}>— {layout.name}</span>}
        </h3>
        {connections.length > 0 && (
          <button
            onClick={() => setShowConnections(!showConnections)}
            style={{
              padding: '5px 12px', borderRadius: '6px', border: '1px solid #334155',
              background: showConnections ? '#1e3a5f' : 'transparent',
              color: showConnections ? '#93c5fd' : '#64748b',
              cursor: 'pointer', fontSize: '11px', fontWeight: 500,
            }}
          >
            {showConnections ? 'Hide Connections' : `Show Connections (${connections.length})`}
          </button>
        )}
      </div>

      <div style={{
        position: 'relative', width: '100%', height: '500px',
        background: '#0f172a', border: '1px solid #334155',
        borderRadius: '8px', overflow: 'hidden',
      }}>
        {/* Connection edges (SVG layer) */}
        {showConnections && visibleConnections.length > 0 && (
          <svg style={{
            position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
            pointerEvents: 'none', zIndex: 5,
          }}>
            {visibleConnections.map(c => {
              const from = positionMap[c.from_resource!];
              const to = positionMap[c.to_resource!];
              const x1 = ((from.x - minX + padding) / (rangeX + padding * 2)) * 100;
              const y1 = ((from.y - minY + padding) / (rangeY + padding * 2)) * 100;
              const x2 = ((to.x - minX + padding) / (rangeX + padding * 2)) * 100;
              const y2 = ((to.y - minY + padding) / (rangeY + padding * 2)) * 100;
              const color = connTypeColor(c.connection_type);

              return (
                <g key={c.identifier}>
                  <line
                    x1={`${x1}%`} y1={`${y1}%`}
                    x2={`${x2}%`} y2={`${y2}%`}
                    stroke={color} strokeWidth="1.5" opacity="0.5"
                    strokeDasharray={c.connection_type === 'path' ? '4,3' : 'none'}
                  />
                  {/* Arrowhead at midpoint */}
                  <circle
                    cx={`${(x1 + x2) / 2}%`} cy={`${(y1 + y2) / 2}%`}
                    r="3" fill={color} opacity="0.7"
                  />
                </g>
              );
            })}
          </svg>
        )}

        {/* Resource nodes */}
        {resources.map(r => {
          const pos = positionMap[r.identifier];
          if (!pos) return null;

          const color = statusColor(statusMap[r.identifier] ?? r.current_status);
          const leftPct = ((pos.x - minX + padding) / (rangeX + padding * 2)) * 100;
          const topPct = ((pos.y - minY + padding) / (rangeY + padding * 2)) * 100;

          return (
            <div
              key={r.identifier}
              title={`${r.name} — ${statusMap[r.identifier] ?? r.current_status ?? 'unknown'} (${pos.x}, ${pos.y})`}
              style={{
                position: 'absolute',
                left: `${leftPct}%`, top: `${topPct}%`,
                width: '22px', height: '22px',
                background: color,
                borderRadius: r.resource_type === 'employee' ? '50%' : '4px',
                border: '2px solid #f1f5f9',
                transform: 'translate(-50%, -50%)',
                cursor: 'pointer', transition: 'background 0.3s',
                zIndex: 10,
                boxShadow: `0 0 8px ${color}80`,
              }}
            />
          );
        })}

        {/* Empty state */}
        {resources.length > 0 && Object.keys(positionMap).length === 0 && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#64748b', fontSize: '14px',
          }}>
            No layout placement data available from the digital twin.
          </div>
        )}
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: '16px', marginTop: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
        {[
          { label: 'Busy', color: '#3b82f6' },
          { label: 'Idle', color: '#22c55e' },
          { label: 'Setup', color: '#f59e0b' },
          { label: 'Paused', color: '#94a3b8' },
          { label: 'Broken', color: '#ef4444' },
          { label: 'Maintenance', color: '#a855f7' },
        ].map(item => (
          <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#cbd5e1' }}>
            <span style={{ width: '12px', height: '12px', background: item.color, borderRadius: '3px', display: 'inline-block' }} />
            {item.label}
          </div>
        ))}
        {connections.length > 0 && (
          <>
            <span style={{ color: '#334155' }}>|</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#cbd5e1' }}>
              <span style={{ width: '12px', height: '2px', background: '#06b6d4', display: 'inline-block' }} />
              Connections ({connections.length})
            </span>
          </>
        )}
      </div>

      <div style={{ marginTop: '12px', fontSize: '12px', color: '#64748b' }}>
        {resources.length} resources · {Object.keys(positionMap).length} with placement data
        {connections.length > 0 && ` · ${visibleConnections.length} connections shown`}
        {' · Live updates via WebSocket'}
      </div>
    </div>
  );
}
