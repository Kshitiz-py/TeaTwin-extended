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

  const selectedMissingDeps = selectedInfo ? getMissingDeps(selectedInfo) : [];
  const isReady = selectedInfo && selectedMissingDeps.length === 0;

  return (
    <div style={{ marginBottom: '14px' }}>
      <style>{`
        @keyframes rp-fadein { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>

      {/* ── Section heading ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
        <span style={{
          width: '28px', height: '28px', borderRadius: '8px',
          background: 'linear-gradient(135deg, #4c1d95, #6366f1)',
          color: '#e0e7ff', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '13px', fontWeight: 700, flexShrink: 0, boxShadow: '0 2px 8px rgba(99,102,241,0.3)',
        }}>1</span>
        <div>
          <h3 style={{ color: '#f1f5f9', margin: 0, fontSize: '14px', fontWeight: 600 }}>
            What do you want to map?
          </h3>
          <p style={{ color: '#64748b', margin: '1px 0 0', fontSize: '11px' }}>
            Independent entities can be mapped now. Dependent ones unlock as their references are mapped.
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
            padding: '11px 14px', background: '#0f172a', border: open ? '1px solid #6366f1' : '1px solid #1e293b',
            borderRadius: '8px', color: '#f1f5f9', fontSize: '13px', cursor: 'pointer',
            fontFamily: 'monospace', textAlign: 'left',
            transition: 'border-color 0.15s, box-shadow 0.15s',
            boxShadow: open ? '0 0 0 3px rgba(99,102,241,0.15)' : 'none',
          }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {selectedEntity && (
              <span style={{
                width: '8px', height: '8px', borderRadius: '50%',
                background: isReady ? '#22c55e' : '#f59e0b',
                boxShadow: `0 0 6px ${isReady ? '#22c55e' : '#f59e0b'}80`,
                flexShrink: 0,
              }} />
            )}
            <span style={{ color: selectedEntity ? '#f1f5f9' : '#64748b' }}>
              {selectedEntity || 'Select a CMSD entity…'}
            </span>
          </div>
          <svg width="12" height="12" viewBox="0 0 12 12" style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}>
            <path d="M3 5l3 3 3-3" stroke="#475569" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
          </svg>
        </button>

        {open && (
          <div style={{
            position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 100,
            background: '#1e293b', border: '1px solid #334155', borderRadius: '10px',
            boxShadow: '0 16px 40px rgba(0,0,0,0.7)',
            maxHeight: '300px', overflowY: 'auto', overflowX: 'hidden',
          }}>
            {available.length > 0 && (
              <div>
                <div style={{
                  padding: '8px 16px', fontSize: '10px', color: '#6ee7b7',
                  fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.8px',
                  background: '#0f172a', position: 'sticky', top: 0, zIndex: 1,
                }}>
                  Available to map ({available.length})
                </div>
                {available.map(e => (
                  <button
                    key={e.name}
                    onClick={() => { onSelect(e.name); setOpen(false); }}
                    style={{
                      width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
                      padding: '9px 16px', border: 'none',
                      background: selectedEntity === e.name ? '#1e3a5f' : 'transparent',
                      color: '#e2e8f0', fontSize: '13px', cursor: 'pointer',
                      fontFamily: 'monospace', textAlign: 'left',
                      transition: 'background 0.1s',
                    }}
                    onMouseEnter={ev => (ev.currentTarget.style.background = selectedEntity === e.name ? '#1e3a5f' : '#1e293b')}
                    onMouseLeave={ev => (ev.currentTarget.style.background = selectedEntity === e.name ? '#1e3a5f' : 'transparent')}
                  >
                    <span style={{ color: '#22c55e', fontSize: '6px', flexShrink: 0 }}>●</span>
                    {e.name}
                  </button>
                ))}
              </div>
            )}

            {blocked.length > 0 && (
              <div>
                <div style={{
                  padding: '8px 16px', fontSize: '10px', color: '#fde68a',
                  fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.8px',
                  background: '#0f172a', position: 'sticky', top: 0, zIndex: 1,
                  borderTop: '1px solid #334155',
                }}>
                  Blocked by dependencies ({blocked.length})
                </div>
                {blocked.map(e => (
                  <button
                    key={e.name}
                    onClick={() => { onSelect(e.name); setOpen(false); }}
                    style={{
                      width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
                      padding: '9px 16px', border: 'none',
                      background: selectedEntity === e.name ? '#422006' : 'transparent',
                      color: '#94a3b8', fontSize: '13px', cursor: 'pointer',
                      fontFamily: 'monospace', textAlign: 'left',
                      transition: 'background 0.1s',
                    }}
                    onMouseEnter={ev => (ev.currentTarget.style.background = selectedEntity === e.name ? '#422006' : '#1e293b')}
                    onMouseLeave={ev => (ev.currentTarget.style.background = selectedEntity === e.name ? '#422006' : 'transparent')}
                  >
                    <span style={{ color: '#f59e0b', fontSize: '6px', flexShrink: 0 }}>●</span>
                    {e.name}
                    <span style={{
                      color: '#f59e0b', fontSize: '10px', marginLeft: 'auto',
                      background: '#422006', padding: '2px 8px', borderRadius: '10px',
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
          marginTop: '10px', padding: '16px 18px',
          background: '#0f172a', borderRadius: '10px',
          border: '1px solid #1e293b',
          animation: 'rp-fadein 0.2s ease',
        }}>
          {/* Description */}
          <p style={{ margin: '0 0 12px', color: '#94a3b8', fontSize: '13px', lineHeight: 1.65 }}>
            {selectedInfo.description}
          </p>

          {/* Availability badge */}
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px',
            padding: '6px 14px', borderRadius: '20px', marginBottom: '10px',
            background: isReady ? '#14532d' : '#422006',
            border: `1px solid ${isReady ? '#166534' : '#78350f'}`,
            color: isReady ? '#86efac' : '#fde68a', fontSize: '12px', fontWeight: 500,
          }}>
            <span>{isReady ? '✓' : '🔒'}</span>
            <span>
              {isReady
                ? 'Ready to map'
                : `Needs ${selectedMissingDeps.join(', ')}`}
            </span>
          </div>

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
              <p style={{ color: '#64748b', fontSize: '12px', margin: 0 }}>
                No mandatory fields — all fields have defaults or are optional. The CMSD model will accept an empty entity.
              </p>
            ) : (
              <FieldTable fields={selectedInfo.fields.filter(f => f.required && !f.has_default)} />
            )}
          </Section>

          {/* Expandable: All CMSD fields */}
          <Section
            label="All CMSD fields"
            count={selectedInfo.fields.length}
            expanded={expandedSections.has('allFields')}
            onToggle={() => toggleSection('allFields')}
          >
            <FieldTable fields={selectedInfo.fields} />
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

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  required: {
    padding: '2px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 600,
    background: '#7f1d1d', color: '#fca5a5', border: '1px solid #991b1b',
    whiteSpace: 'nowrap' as const,
  },
  optional: {
    padding: '2px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 500,
    background: '#1e293b', color: '#94a3b8', border: '1px solid #334155',
    whiteSpace: 'nowrap' as const,
  },
  defaulted: {
    padding: '2px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 500,
    background: '#0f1a2e', color: '#64748b', border: '1px solid #1e293b',
    whiteSpace: 'nowrap' as const,
  },
  reference: {
    padding: '2px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 600,
    background: '#1e1b4b', color: '#a5b4fc', border: '1px solid #3730a3',
    whiteSpace: 'nowrap' as const,
  },
};

function FieldTable({ fields }: { fields: CatalogField[] }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {fields.map((f, i) => {
        let statusKey: string;
        let statusLabel: string;
        if (f.is_reference) {
          statusKey = 'reference';
          statusLabel = 'reference';
        } else if (f.required && !f.has_default) {
          statusKey = 'required';
          statusLabel = 'required';
        } else if (f.has_default) {
          statusKey = 'defaulted';
          statusLabel = 'has default';
        } else {
          statusKey = 'optional';
          statusLabel = 'optional';
        }
        return (
          <div key={f.name} style={{
            display: 'flex', alignItems: 'center', gap: '12px',
            padding: '6px 10px',
            background: i % 2 === 0 ? 'transparent' : 'rgba(15,23,42,0.5)',
            borderRadius: '6px',
          }}>
            <code style={{
              color: f.required && !f.has_default ? '#fca5a5' : '#e2e8f0',
              fontFamily: 'monospace', fontSize: '12px', fontWeight: 500,
              minWidth: '150px', flexShrink: 0,
            }}>
              {f.name}
            </code>
            <code style={{
              color: '#64748b', fontFamily: 'monospace', fontSize: '11px',
              minWidth: '110px', flexShrink: 0,
            }}>
              {f.type}
            </code>
            <span style={STATUS_STYLE[statusKey]}>{statusLabel}</span>
            {f.description && (
              <span style={{
                color: '#64748b', fontSize: '11px', flex: 1,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const,
              }}>
                {f.description}
              </span>
            )}
          </div>
        );
      })}
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
    <div style={{ borderTop: '1px solid rgba(51,65,85,0.4)' }}>
      <button
        onClick={onToggle}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: '8px',
          padding: '8px 0', border: 'none', background: 'transparent',
          color: expanded ? '#e2e8f0' : '#94a3b8', fontSize: '11px', cursor: 'pointer',
          fontWeight: 500, textAlign: 'left',
        }}>
        <svg width="10" height="10" viewBox="0 0 10 10" style={{
          transform: expanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s',
          flexShrink: 0,
        }}>
          <path d="M4 2l3 3-3 3" stroke={expanded ? '#818cf8' : '#475569'} strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        {label}
        {count > 0 && (
          <span style={{
            padding: '0 6px', borderRadius: '10px', background: '#1e293b',
            color: '#64748b', fontSize: '10px', fontWeight: 600, lineHeight: '16px',
          }}>
            {count}
          </span>
        )}
      </button>
      {expanded && (
        <div style={{ padding: '0 0 10px 20px' }}>
          {children}
        </div>
      )}
    </div>
  );
}
