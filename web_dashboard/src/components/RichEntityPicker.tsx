import { useState, useEffect, useMemo } from 'react';

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
}

type EntityAvailability = 'available' | 'blocked';

export default function RichEntityPicker({ selectedEntity, onSelect, existingEntities }: RichEntityPickerProps) {
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [open, setOpen] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['references']));

  useEffect(() => {
    fetch('/api/agent/v1/cmsd-catalog')
      .then(r => r.json())
      .then(setCatalog)
      .catch(() => {});
  }, []);

  const { available, blocked, selectedInfo } = useMemo(() => {
    if (!catalog) return { available: [] as CatalogEntity[], blocked: [] as CatalogEntity[], selectedInfo: null };

    const avail: CatalogEntity[] = [];
    const blk: CatalogEntity[] = [];

    for (const entity of Object.values(catalog.entities)) {
      const missingDeps = entity.references.filter(ref => !existingEntities.has(ref));
      if (missingDeps.length === 0) {
        avail.push(entity);
      } else {
        blk.push(entity);
      }
    }

    // Sort alphabetically within each group
    avail.sort((a, b) => a.name.localeCompare(b.name));
    blk.sort((a, b) => a.name.localeCompare(b.name));

    const info = catalog.entities[selectedEntity] || null;

    return { available: avail, blocked: blk, selectedInfo: info };
  }, [catalog, selectedEntity, existingEntities]);

  const toggleSection = (name: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name); else next.add(name);
      return next;
    });
  };

  const getMissingDeps = (entity: CatalogEntity): string[] => {
    if (!catalog) return [];
    return entity.references.filter(ref => !existingEntities.has(ref));
  };

  return (
    <div style={{ marginBottom: '14px' }}>
      <style>{`
        @keyframes rp-fadein { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>

      {/* ── Section heading ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px',
      }}>
        <span style={{
          width: '28px', height: '28px', borderRadius: '8px',
          background: '#312e81', color: '#a5b4fc',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '14px', fontWeight: 700, flexShrink: 0,
        }}>1</span>
        <div>
          <h3 style={{ color: '#f1f5f9', margin: 0, fontSize: '14px', fontWeight: 600 }}>
            What do you want to map?
          </h3>
          <p style={{ color: '#64748b', margin: '1px 0 0', fontSize: '11px' }}>
            Select a CMSD entity. Independent entities are available immediately; dependent ones unlock as their references are mapped.
          </p>
        </div>
      </div>

      {/* ── Dropdown ── */}
      <div style={{ position: 'relative' }}>
        <button
          onClick={() => setOpen(!open)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '10px 14px', background: '#0f172a', border: '1px solid #334155',
            borderRadius: '8px', color: '#f1f5f9', fontSize: '13px', cursor: 'pointer',
            fontFamily: 'monospace', textAlign: 'left',
            transition: 'border-color 0.15s',
          }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {selectedEntity && (
              <span style={{
                width: '8px', height: '8px', borderRadius: '50%',
                background: getMissingDeps(selectedInfo || { name: '', description: '', fields: [], references: [], hierarchy: '', example: {} }).length === 0 ? '#22c55e' : '#f59e0b',
                flexShrink: 0,
              }} />
            )}
            <span style={{ color: selectedEntity ? '#f1f5f9' : '#64748b' }}>
              {selectedEntity || 'Select a CMSD entity…'}
            </span>
          </div>
          <span style={{ color: '#475569', fontSize: '12px' }}>{open ? '▲' : '▼'}</span>
        </button>

        {open && (
          <div style={{
            position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100,
            background: '#1e293b', border: '1px solid #334155', borderRadius: '8px',
            marginTop: '4px', boxShadow: '0 12px 32px rgba(0,0,0,0.6)',
            maxHeight: '320px', overflowY: 'auto',
          }}>
            {available.length > 0 && (
              <div>
                <div style={{
                  padding: '8px 14px', fontSize: '10px', color: '#86efac',
                  fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.6px',
                  background: '#0f172a', position: 'sticky', top: 0,
                  borderBottom: '1px solid #1e293b',
                }}>
                  Available to map ({available.length})
                </div>
                {available.map(e => (
                  <button
                    key={e.name}
                    onClick={() => { onSelect(e.name); setOpen(false); }}
                    style={{
                      width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
                      padding: '8px 14px', border: 'none',
                      background: selectedEntity === e.name ? '#1e3a5f' : 'transparent',
                      color: '#e2e8f0', fontSize: '13px', cursor: 'pointer',
                      fontFamily: 'monospace', textAlign: 'left',
                    }}>
                    <span style={{ color: '#22c55e', fontSize: '8px', flexShrink: 0 }}>●</span>
                    {e.name}
                  </button>
                ))}
              </div>
            )}

            {blocked.length > 0 && (
              <div>
                <div style={{
                  padding: '8px 14px', fontSize: '10px', color: '#fde68a',
                  fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.6px',
                  background: '#0f172a', position: 'sticky', top: 0,
                  borderTop: '1px solid #334155', borderBottom: '1px solid #1e293b',
                }}>
                  Blocked by dependencies ({blocked.length})
                </div>
                {blocked.map(e => (
                  <button
                    key={e.name}
                    onClick={() => { onSelect(e.name); setOpen(false); }}
                    style={{
                      width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
                      padding: '8px 14px', border: 'none',
                      background: selectedEntity === e.name ? '#422006' : 'transparent',
                      color: '#94a3b8', fontSize: '13px', cursor: 'pointer',
                      fontFamily: 'monospace', textAlign: 'left',
                    }}>
                    <span style={{ color: '#f59e0b', fontSize: '8px', flexShrink: 0 }}>●</span>
                    {e.name}
                    <span style={{
                      color: '#f59e0b', fontSize: '10px', marginLeft: 'auto',
                      background: '#422006', padding: '1px 6px', borderRadius: '8px',
                    }}>
                      needs {getMissingDeps(e).join(', ')}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Entity detail panel ── */}
      {selectedInfo && (
        <div style={{
          marginTop: '10px', padding: '16px',
          background: '#0f172a', borderRadius: '10px', border: '1px solid #1e293b',
          animation: 'rp-fadein 0.15s ease',
        }}>
          {/* Always visible: description + availability */}
          <p style={{ margin: '0 0 10px', color: '#94a3b8', fontSize: '13px', lineHeight: 1.6 }}>
            {selectedInfo.description}
          </p>

          {(() => {
            const missing = getMissingDeps(selectedInfo);
            if (missing.length === 0) {
              return (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  padding: '8px 12px', borderRadius: '6px', marginBottom: '8px',
                  background: '#14532d', border: '1px solid #166534',
                  color: '#86efac', fontSize: '12px',
                }}>
                  <span style={{ fontSize: '14px' }}>✓</span>
                  <span>Ready to map — all dependencies satisfied</span>
                </div>
              );
            }
            return (
              <div style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                padding: '8px 12px', borderRadius: '6px', marginBottom: '8px',
                background: '#422006', border: '1px solid #78350f',
                color: '#fde68a', fontSize: '12px',
              }}>
                <span style={{ fontSize: '14px' }}>🔒</span>
                <span>
                  Cannot map yet — needs{' '}
                  <strong style={{ color: '#fbbf24' }}>{missing.join(', ')}</strong>
                  {' '}to be mapped first
                </span>
              </div>
            );
          })()}

          {/* Expandable: References */}
          <Section
            label="References"
            count={selectedInfo.references.length}
            expanded={expandedSections.has('references')}
            onToggle={() => toggleSection('references')}
          >
            {selectedInfo.references.length === 0 ? (
              <p style={{ color: '#64748b', fontSize: '11px', margin: 0 }}>
                This entity does not reference any other CMSD entities.
              </p>
            ) : (
              <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                {selectedInfo.references.map(ref => {
                  const exists = existingEntities.has(ref);
                  return (
                    <span key={ref} style={{
                      padding: '2px 8px', borderRadius: '10px', fontSize: '11px',
                      fontFamily: 'monospace',
                      background: exists ? '#14532d' : '#1e1b4b',
                      border: exists ? '1px solid #166534' : '1px solid #3730a3',
                      color: exists ? '#86efac' : '#a5b4fc',
                    }}>
                      {ref} {exists ? '' : '(not mapped)'}
                    </span>
                  );
                })}
              </div>
            )}
            <p style={{ color: '#64748b', fontSize: '10px', margin: '6px 0 0' }}>
              {selectedInfo.hierarchy}
            </p>
          </Section>

          {/* Expandable: Required fields */}
          <Section
            label="Fields you must provide"
            count={selectedInfo.fields.filter(f => f.required && !f.has_default).length}
            expanded={expandedSections.has('required')}
            onToggle={() => toggleSection('required')}
          >
            {selectedInfo.fields.filter(f => f.required && !f.has_default).length === 0 ? (
              <p style={{ color: '#64748b', fontSize: '11px', margin: 0 }}>
                No mandatory fields — all fields have defaults or are optional. The CMSD model will accept an empty entity.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                {selectedInfo.fields.filter(f => f.required && !f.has_default).map(f => (
                  <div key={f.name} style={{ display: 'flex', gap: '10px', fontSize: '11px' }}>
                    <code style={{ color: '#fca5a5', minWidth: '100px', fontFamily: 'monospace' }}>{f.name}</code>
                    <span style={{ color: '#64748b' }}>{f.type}</span>
                    {f.description && <span style={{ color: '#475569' }}>— {f.description}</span>}
                  </div>
                ))}
              </div>
            )}
          </Section>

          {/* Expandable: All CMSD fields */}
          <Section
            label={`All CMSD fields (${selectedInfo.fields.length})`}
            count={selectedInfo.fields.length}
            expanded={expandedSections.has('allFields')}
            onToggle={() => toggleSection('allFields')}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              {selectedInfo.fields.map(f => (
                <div key={f.name} style={{ display: 'flex', gap: '10px', fontSize: '11px', alignItems: 'baseline' }}>
                  <code style={{
                    color: f.required && !f.has_default ? '#fca5a5' : '#e2e8f0',
                    minWidth: '130px', fontFamily: 'monospace',
                  }}>
                    {f.name}
                  </code>
                  <span style={{ color: '#64748b', minWidth: '100px', fontSize: '10px' }}>{f.type}</span>
                  <span style={{ color: '#475569', fontSize: '10px' }}>
                    {f.required && !f.has_default ? 'required' : f.has_default ? 'has default' : 'optional'}
                    {f.is_reference ? ' · reference' : ''}
                  </span>
                  {f.description && (
                    <span style={{ color: '#64748b', flex: 1, fontSize: '10px' }}>{f.description}</span>
                  )}
                </div>
              ))}
            </div>
          </Section>

          {/* Expandable: Example payload */}
          <Section
            label="Example API payload"
            count={0}
            expanded={expandedSections.has('example')}
            onToggle={() => toggleSection('example')}
          >
            <pre style={{
              margin: 0, padding: '8px 10px',
              background: '#1e293b', borderRadius: '4px',
              border: '1px solid #334155',
              color: '#e2e8f0', fontSize: '11px', fontFamily: 'monospace',
              overflowX: 'auto', whiteSpace: 'pre',
            }}>
              {JSON.stringify(selectedInfo.example, null, 2)}
            </pre>
          </Section>
        </div>
      )}
    </div>
  );
}

function Section({ label, count, expanded, onToggle, children }: {
  label: string;
  count: number;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div style={{
      borderTop: '1px solid #1e293b',
      marginTop: '2px',
    }}>
      <button
        onClick={onToggle}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: '8px',
          padding: '8px 0', border: 'none', background: 'transparent',
          color: '#94a3b8', fontSize: '12px', cursor: 'pointer',
          fontWeight: 500, textAlign: 'left',
        }}>
        <span style={{
          color: expanded ? '#818cf8' : '#475569',
          fontSize: '10px', transition: 'transform 0.15s',
        }}>{expanded ? '▾' : '▸'}</span>
        {label}
        {count > 0 && (
          <span style={{
            padding: '0 7px', borderRadius: '10px', background: '#1e293b',
            color: '#64748b', fontSize: '10px', fontWeight: 600,
          }}>
            {count}
          </span>
        )}
      </button>
      {expanded && (
        <div style={{ padding: '0 0 10px 22px' }}>
          {children}
        </div>
      )}
    </div>
  );
}
