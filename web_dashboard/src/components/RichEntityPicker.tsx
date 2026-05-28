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

      {/* ── Dropdown ── */}
      <div style={{ position: 'relative' }}>
        <label style={{
          fontSize: '11px', color: '#94a3b8', display: 'block', marginBottom: '4px',
          fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px',
        }}>
          What do you want to map?
        </label>

        <button
          onClick={() => setOpen(!open)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '8px 12px', background: '#0f172a', border: '1px solid #334155',
            borderRadius: '6px', color: '#f1f5f9', fontSize: '13px', cursor: 'pointer',
            fontFamily: 'monospace', textAlign: 'left',
          }}>
          <span style={{ color: selectedEntity ? '#f1f5f9' : '#64748b' }}>
            {selectedEntity || 'Select a CMSD entity...'}
          </span>
          <span style={{ color: '#475569', fontSize: '11px' }}>{open ? '▴' : '▾'}</span>
        </button>

        {open && (
          <div style={{
            position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100,
            background: '#1e293b', border: '1px solid #334155', borderRadius: '8px',
            marginTop: '4px', boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
            maxHeight: '320px', overflowY: 'auto',
          }}>
            {/* Available section */}
            {available.length > 0 && (
              <div>
                <div style={{
                  padding: '6px 12px', fontSize: '10px', color: '#22c55e',
                  fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px',
                  background: '#0f172a', position: 'sticky', top: 0,
                }}>
                  Available to map ({available.length})
                </div>
                {available.map(e => (
                  <button
                    key={e.name}
                    onClick={() => { onSelect(e.name); setOpen(false); }}
                    style={{
                      width: '100%', display: 'flex', alignItems: 'center', gap: '8px',
                      padding: '6px 12px', border: 'none', background: selectedEntity === e.name ? '#1e3a5f' : 'transparent',
                      color: '#e2e8f0', fontSize: '12px', cursor: 'pointer',
                      fontFamily: 'monospace', textAlign: 'left',
                    }}>
                    <span style={{ color: '#22c55e', fontSize: '8px' }}>●</span>
                    {e.name}
                  </button>
                ))}
              </div>
            )}

            {/* Blocked section */}
            {blocked.length > 0 && (
              <div>
                <div style={{
                  padding: '6px 12px', fontSize: '10px', color: '#f59e0b',
                  fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px',
                  background: '#0f172a', position: 'sticky', top: 0,
                  borderTop: '1px solid #334155',
                }}>
                  Blocked by dependencies ({blocked.length})
                </div>
                {blocked.map(e => (
                  <button
                    key={e.name}
                    onClick={() => { onSelect(e.name); setOpen(false); }}
                    style={{
                      width: '100%', display: 'flex', alignItems: 'center', gap: '8px',
                      padding: '6px 12px', border: 'none', background: selectedEntity === e.name ? '#422006' : 'transparent',
                      color: '#94a3b8', fontSize: '12px', cursor: 'pointer',
                      fontFamily: 'monospace', textAlign: 'left',
                    }}>
                    <span style={{ color: '#f59e0b', fontSize: '8px' }}>●</span>
                    {e.name}
                    <span style={{ color: '#f59e0b', fontSize: '10px', marginLeft: 'auto' }}>
                      needs {getMissingDeps(e).join(', ')}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Entity detail panel (progressive disclosure) ── */}
      {selectedInfo && (
        <div style={{
          marginTop: '10px', padding: '14px 16px',
          background: '#0f172a', borderRadius: '8px', border: '1px solid #334155',
          animation: 'rp-fadein 0.15s ease',
        }}>
          {/* Always visible: description + availability */}
          <p style={{ margin: '0 0 8px', color: '#94a3b8', fontSize: '12px', lineHeight: 1.5 }}>
            {selectedInfo.description}
          </p>

          {(() => {
            const missing = getMissingDeps(selectedInfo);
            if (missing.length === 0) {
              return (
                <div style={{
                  padding: '6px 10px', borderRadius: '4px',
                  background: '#14532d', border: '1px solid #166534',
                  color: '#86efac', fontSize: '11px', fontWeight: 500,
                  marginBottom: '8px',
                }}>
                  ✓ Available to map — all dependencies satisfied
                </div>
              );
            }
            return (
              <div style={{
                padding: '6px 10px', borderRadius: '4px',
                background: '#422006', border: '1px solid #78350f',
                color: '#fde68a', fontSize: '11px', fontWeight: 500,
                marginBottom: '8px',
              }}>
                🔒 Cannot map yet — {selectedInfo.name} references{' '}
                <strong style={{ color: '#fbbf24' }}>{missing.join(', ')}</strong>
                {missing.length === 1 ? ', which has' : ', which have'} not been mapped.
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
    <div style={{ marginTop: '4px' }}>
      <button
        onClick={onToggle}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: '6px',
          padding: '4px 0', border: 'none', background: 'transparent',
          color: '#64748b', fontSize: '11px', cursor: 'pointer',
          fontWeight: 500, textAlign: 'left',
        }}>
        <span style={{ fontSize: '10px', color: '#475569' }}>{expanded ? '▾' : '▸'}</span>
        {label}
        {count > 0 && (
          <span style={{
            padding: '0 6px', borderRadius: '8px', background: '#1e293b',
            color: '#64748b', fontSize: '10px',
          }}>
            {count}
          </span>
        )}
      </button>
      {expanded && (
        <div style={{ paddingLeft: '16px', paddingTop: '4px', paddingBottom: '4px' }}>
          {children}
        </div>
      )}
    </div>
  );
}
