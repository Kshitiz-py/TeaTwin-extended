import { useState, useEffect, useMemo } from 'react';
import { agentApi, MappingSummary } from '../services/agentApi';

interface CatalogField {
  name: string;
  type: string;
  required: boolean;
  has_default: boolean;
  is_reference: boolean;
  description: string;
}

interface CatalogEntity {
  name: string;
  description: string;
  fields: CatalogField[];
  references: string[];
  hierarchy: string;
  example: Record<string, any>;
}

interface CatalogResponse {
  entities: Record<string, CatalogEntity>;
}

interface RichEntityPickerProps {
  selectedEntity: string;
  onSelect: (entity: string) => void;
  existingEntities: Set<string>;
  existingMappings: Array<{ cmsd_entity: string; relation_targets?: string[] }>;
  onContinue: () => void;
  canContinue: boolean;
}

export default function RichEntityPicker({
  selectedEntity, onSelect, existingEntities, existingMappings, onContinue, canContinue,
}: RichEntityPickerProps) {
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<'all' | 'ready' | 'blocked' | 'mapped'>('ready');

  useEffect(() => {
    fetch('/api/agent/v1/cmsd-catalog')
      .then(r => r.json())
      .then(setCatalog)
      .catch(() => {});
  }, []);

  // Build dynamic dependency map from relation_targets
  const dynDeps = useMemo(() => {
    const map: Record<string, string[]> = {};
    for (const m of existingMappings) {
      const targets = m.relation_targets || [];
      if (targets.length > 0) {
        if (!map[m.cmsd_entity]) map[m.cmsd_entity] = [];
        map[m.cmsd_entity].push(...targets);
      }
    }
    return map;
  }, [existingMappings]);

  // Derive dependency state for each entity
  const getEntityState = (entityName: string): { status: 'mapped' | 'ready' | 'blocked'; missingDeps: string[] } => {
    if (existingEntities.has(entityName)) return { status: 'mapped', missingDeps: [] };
    const deps = dynDeps[entityName] || [];
    const missing = deps.filter(d => !existingEntities.has(d));
    if (missing.length > 0) return { status: 'blocked', missingDeps: missing };
    return { status: 'ready', missingDeps: [] };
  };

  const toggleExpand = (name: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name); else next.add(name);
      return next;
    });
  };

  if (!catalog) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
        Loading CMSD catalog...
      </div>
    );
  }

  const entities = Object.values(catalog.entities);

  const filtered = entities.filter(e => {
    const state = getEntityState(e.name);
    switch (filter) {
      case 'ready': return state.status === 'ready';
      case 'blocked': return state.status === 'blocked';
      case 'mapped': return state.status === 'mapped';
      default: return true;
    }
  });

  const counts = {
    ready: entities.filter(e => getEntityState(e.name).status === 'ready').length,
    blocked: entities.filter(e => getEntityState(e.name).status === 'blocked').length,
    mapped: entities.filter(e => getEntityState(e.name).status === 'mapped').length,
  };

  return (
    <div style={{ marginBottom: '16px' }}>
      {/* ── Header ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '10px',
      }}>
        <div>
          <h3 style={{ color: '#f1f5f9', margin: 0, fontSize: '15px' }}>
            What do you want to map?
          </h3>
          <p style={{ color: '#94a3b8', margin: '2px 0 0', fontSize: '12px' }}>
            Select a CMSD entity. Independent entities should be mapped first.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '4px' }}>
          {([
            ['ready', counts.ready, '#22c55e'],
            ['blocked', counts.blocked, '#f59e0b'],
            ['mapped', counts.mapped, '#3b82f6'],
          ] as const).map(([key, count, color]) => (
            <button key={key} onClick={() => setFilter(key)}
              style={{
                padding: '4px 10px', borderRadius: '14px', fontSize: '11px', fontWeight: 600,
                border: filter === key ? `1.5px solid ${color}` : '1px solid #334155',
                background: filter === key ? `${color}18` : '#1e293b',
                color: filter === key ? color : '#64748b',
                cursor: 'pointer',
              }}>
              {key === 'ready' ? '✓ Ready' : key === 'blocked' ? '🔒 Blocked' : 'Mapped'} ({count})
            </button>
          ))}
        </div>
      </div>

      {/* ── Entity cards ── */}
      <div style={{ display: 'grid', gap: '8px', maxHeight: '420px', overflowY: 'auto' }}>
        {filtered.length === 0 && (
          <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
            No entities match this filter.
          </div>
        )}
        {filtered.map(entity => {
          const state = getEntityState(entity.name);
          const isSelected = selectedEntity === entity.name;
          const isExpanded = expanded.has(entity.name);

          const requiredFields = entity.fields.filter(f => f.required && !f.has_default);
          const optionalFields = entity.fields.filter(f => !f.required || f.has_default);
          const refFields = entity.fields.filter(f => f.is_reference);

          const stateColors: Record<string, string> = {
            ready: '#22c55e',
            blocked: '#f59e0b',
            mapped: '#3b82f6',
          };
          const stateLabels: Record<string, string> = {
            ready: 'Ready to map',
            blocked: 'Dependencies missing',
            mapped: 'Already mapped',
          };

          return (
            <div key={entity.name} style={{
              background: isSelected ? '#0f172a' : '#1e293b',
              borderRadius: '10px',
              border: isSelected ? '2px solid #6366f1' : '1px solid #334155',
              opacity: state.status === 'mapped' ? 0.7 : 1,
              transition: 'border 0.15s',
            }}>
              {/* ── Card header (always visible) ── */}
              <div
                onClick={() => { onSelect(entity.name); toggleExpand(entity.name); }}
                style={{
                  display: 'flex', alignItems: 'center', gap: '12px',
                  padding: '12px 16px', cursor: 'pointer',
                }}>
                {/* Status dot */}
                <span style={{
                  width: '10px', height: '10px', borderRadius: '50%',
                  background: stateColors[state.status],
                  flexShrink: 0,
                }} title={stateLabels[state.status]} />

                {/* Entity name + brief */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: '#f1f5f9', fontSize: '14px', fontWeight: 600 }}>
                      {entity.name}
                    </span>
                    <span style={{
                      fontSize: '10px', padding: '2px 6px', borderRadius: '8px',
                      background: stateColors[state.status] + '20',
                      color: stateColors[state.status],
                      fontWeight: 600, whiteSpace: 'nowrap',
                    }}>
                      {stateLabels[state.status]}
                    </span>
                    {refFields.length > 0 && (
                      <span style={{
                        fontSize: '10px', padding: '2px 6px', borderRadius: '8px',
                        background: '#312e81', color: '#a5b4fc',
                      }}>
                        {refFields.length} ref{refFields.length > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                  <p style={{ margin: '2px 0 0', color: '#64748b', fontSize: '11px', lineHeight: 1.4 }}>
                    {entity.description.slice(0, 120)}{entity.description.length > 120 ? '...' : ''}
                  </p>
                </div>

                {/* Expand arrow */}
                <span style={{ color: '#475569', fontSize: '16px', flexShrink: 0 }}>
                  {isExpanded ? '▾' : '▸'}
                </span>
              </div>

              {/* ── Expanded detail ── */}
              {isExpanded && (
                <div style={{
                  padding: '0 16px 14px', borderTop: '1px solid #1e293b',
                }}>
                  {/* Block reason */}
                  {state.status === 'blocked' && (
                    <div style={{
                      padding: '8px 12px', marginTop: '10px',
                      background: '#422006', borderRadius: '6px',
                      border: '1px solid #78350f',
                    }}>
                      <span style={{ color: '#fde68a', fontSize: '11px', fontWeight: 600 }}>
                        Cannot map yet — depends on: {state.missingDeps.join(', ')}
                      </span>
                      <span style={{ color: '#fbbf24', fontSize: '11px', marginLeft: '4px' }}>
                        {state.missingDeps.length === 1
                          ? `(map ${state.missingDeps[0]} first)`
                          : `(map ${state.missingDeps.slice(0, -1).join(', ')} and ${state.missingDeps[state.missingDeps.length - 1]} first)`}
                      </span>
                    </div>
                  )}

                  {/* Hierarchy */}
                  <div style={{ marginTop: '10px' }}>
                    <span style={{ fontSize: '10px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Hierarchy</span>
                    <p style={{ margin: '2px 0 0', color: '#94a3b8', fontSize: '12px' }}>
                      {entity.hierarchy}
                    </p>
                  </div>

                  {/* Fields summary */}
                  <div style={{ marginTop: '10px' }}>
                    <span style={{ fontSize: '10px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Fields ({entity.fields.length} total)
                    </span>
                    <div style={{ display: 'flex', gap: '16px', marginTop: '4px', flexWrap: 'wrap' }}>
                      {requiredFields.length > 0 && (
                        <span style={{ fontSize: '11px', color: '#fca5a5' }}>
                          {requiredFields.length} required: {requiredFields.map(f => f.name).join(', ')}
                        </span>
                      )}
                      <span style={{ fontSize: '11px', color: '#64748b' }}>
                        {optionalFields.length} optional (with defaults)
                      </span>
                    </div>
                  </div>

                  {/* References */}
                  {entity.references.length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      <span style={{ fontSize: '10px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.5px' }}>References</span>
                      <div style={{ display: 'flex', gap: '6px', marginTop: '4px', flexWrap: 'wrap' }}>
                        {entity.references.map(ref => (
                          <span key={ref} style={{
                            padding: '2px 8px', borderRadius: '10px',
                            background: existingEntities.has(ref) ? '#14532d' : '#1e1b4b',
                            border: existingEntities.has(ref) ? '1px solid #22c55e' : '1px solid #3730a3',
                            color: existingEntities.has(ref) ? '#86efac' : '#a5b4fc',
                            fontSize: '11px', fontFamily: 'monospace',
                          }}>
                            {ref} {existingEntities.has(ref) ? '✓' : ''}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Example payload */}
                  <div style={{ marginTop: '10px' }}>
                    <span style={{ fontSize: '10px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Example API payload
                    </span>
                    <pre style={{
                      margin: '4px 0 0', padding: '8px 10px',
                      background: '#0f172a', borderRadius: '4px',
                      border: '1px solid #1e293b',
                      color: '#e2e8f0', fontSize: '11px', fontFamily: 'monospace',
                      overflowX: 'auto', whiteSpace: 'pre',
                    }}>
                      {JSON.stringify(entity.example, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* ── Select indicator for non-expanded ── */}
              {isSelected && !isExpanded && (
                <div style={{
                  padding: '0 16px 12px', display: 'flex', alignItems: 'center', gap: '6px',
                }}>
                  <span style={{ color: '#818cf8', fontSize: '11px' }}>
                    Selected — provide API endpoints below
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Continue button ── */}
      {selectedEntity && getEntityState(selectedEntity).status !== 'blocked' && (
        <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'flex-end' }}>
          <button onClick={onContinue} disabled={!canContinue} style={{
            padding: '10px 28px', borderRadius: '6px', border: 'none',
            background: canContinue ? '#22c55e' : '#334155',
            color: canContinue ? '#fff' : '#64748b',
            cursor: canContinue ? 'pointer' : 'not-allowed',
            fontSize: '14px', fontWeight: 700,
          }}>
            Continue with {selectedEntity} →
          </button>
        </div>
      )}
    </div>
  );
}
