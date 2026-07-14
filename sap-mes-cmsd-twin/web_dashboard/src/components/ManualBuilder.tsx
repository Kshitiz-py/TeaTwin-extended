import { useState, useEffect, useMemo } from 'react';
import { agentApi } from '../services/agentApi';

interface CatalogEntity {
  name: string;
  description: string;
  fields: Array<{ name: string; type: string; required: boolean; has_default: boolean; is_reference: boolean }>;
  references: string[];
  hierarchy: string;
}

interface CatalogResponse {
  entities: Record<string, CatalogEntity>;
}

interface ManualBuilderProps {
  preset?: { entityType: string; identifiers: string[] } | null;
  onPresetConsumed?: () => void;
}

export default function ManualBuilder({ preset, onPresetConsumed }: ManualBuilderProps) {
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [entityType, setEntityType] = useState('');
  const [entries, setEntries] = useState<Array<Record<string, string>>>([{ identifier: '', name: '' }]);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [presetApplied, setPresetApplied] = useState(false);

  useEffect(() => {
    fetch('/api/agent/v1/cmsd-catalog')
      .then(r => r.json())
      .then(setCatalog)
      .catch(() => {});
  }, []);

  // Apply preset when catalog is loaded and preset hasn't been consumed yet
  useEffect(() => {
    if (!preset || !catalog || presetApplied) return;
    const entity = catalog.entities[preset.entityType];
    if (!entity) return;

    setEntityType(preset.entityType);
    const reqFields = entity.fields.filter(f => {
      if (f.name === 'identifier') return true;
      return f.required && !f.has_default && !f.is_reference;
    });
    // Create one entry per missing identifier, pre-filling the identifier field.
    // If no specific identifiers are known (from preflight), create one blank row.
    const ids = preset.identifiers.length > 0 ? preset.identifiers : [''];
    const presetEntries = ids.map(id => {
      const entry: Record<string, string> = {};
      for (const f of reqFields) {
        entry[f.name] = f.name === 'identifier' ? id : '';
      }
      return entry;
    });
    setEntries(presetEntries);
    setPresetApplied(true);
    onPresetConsumed?.();
  }, [preset, catalog, presetApplied, onPresetConsumed]);

  const entityInfo = catalog?.entities[entityType] || null;

  // Mandatory non-reference fields. Always include 'identifier' as minimum.
  const mandatoryFields = entityInfo
    ? entityInfo.fields.filter(f => {
        if (f.name === 'identifier') return true;
        return f.required && !f.has_default && !f.is_reference;
      })
    : [];

  // Reset entries when entity type changes
  const handleEntityChange = (newType: string) => {
    setEntityType(newType);
    setFeedback(null);
    const info = catalog?.entities[newType];
    if (info) {
      const reqFields = info.fields.filter(f => {
        if (f.name === 'identifier') return true;
        return f.required && !f.has_default && !f.is_reference;
      });
      const defaults: Record<string, string> = {};
      for (const f of reqFields) {
        defaults[f.name] = '';
      }
      setEntries([defaults]);
    }
  };

  const updateEntry = (idx: number, field: string, value: string) => {
    setEntries(prev => {
      const next = [...prev];
      next[idx] = { ...next[idx], [field]: value };
      return next;
    });
  };

  const addEntry = () => {
    const defaults: Record<string, string> = {};
    for (const f of mandatoryFields) {
      defaults[f.name] = '';
    }
    setEntries(prev => [...prev, defaults]);
  };

  const removeEntry = (idx: number) => {
    setEntries(prev => prev.filter((_, i) => i !== idx));
  };

  const canSave = useMemo(() => {
    if (!entityType || entries.length === 0) return false;
    return entries.every(e => e.identifier && e.identifier.trim() !== '');
  }, [entityType, entries]);

  const handleSave = async () => {
    if (!canSave || !entityType) return;
    setSaving(true);
    setFeedback(null);
    try {
      const result = await agentApi.createManualMapping(entityType, entries);
      setFeedback({ type: 'success', message: `${result.message} — ${result.mapping_id}` });
    } catch (e: any) {
      setFeedback({ type: 'error', message: e.message || 'Failed to save' });
    } finally {
      setSaving(false);
    }
  };

  const entityOptions = catalog
    ? Object.values(catalog.entities).sort((a, b) => a.name.localeCompare(b.name))
    : [];

  return (
    <div style={{ padding: '0 4px' }}>
      <style>{`
        @keyframes mb-fadein { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>

      {/* Header */}
      <div style={{ marginBottom: '16px' }}>
        <h2 style={{ color: '#f1f5f9', fontSize: '16px', fontWeight: 600, margin: '0 0 4px' }}>
          Manual Entity Builder
        </h2>
        <p style={{ color: '#64748b', fontSize: '12px', margin: 0 }}>
          Create CMSD-compliant demo entities when no API provides the data. These feed into
          relation resolution so dependent entities can be built.
        </p>
      </div>

      {/* Preset banner: guided from relation errors */}
      {preset && presetApplied && (
        <div style={{
          padding: '10px 14px', marginBottom: '16px', borderRadius: '8px',
          background: '#1e1b4b', border: '1px solid #3730a3',
          color: '#c7d2fe', fontSize: '12px',
          display: 'flex', alignItems: 'center', gap: '8px',
        }}>
          <span style={{ fontSize: '14px' }}>→</span>
          <span>
            Guided create: <strong>{preset.entityType}</strong>
            {preset.identifiers.length > 0
              ? <> — {preset.identifiers.length} missing identifier(s): {preset.identifiers.join(', ')}</>
              : <> — enter the identifier(s) that your mapping references</>
            }.
            Fill remaining fields and save to resolve.
          </span>
        </div>
      )}

      {/* Entity selector */}
      <div style={{ marginBottom: '16px' }}>
        <label style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', display: 'block', marginBottom: '6px' }}>
          Entity Type
        </label>
        {entityOptions.length === 0 ? (
          <div style={{ color: '#64748b', fontSize: '12px' }}>Loading catalog…</div>
        ) : (
          <select
            value={entityType}
            onChange={e => handleEntityChange(e.target.value)}
            style={{
              width: '100%', padding: '9px 12px',
              background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px',
              color: '#f1f5f9', fontSize: '13px', fontFamily: 'monospace',
            }}
          >
            <option value="">-- Select entity type --</option>
            {entityOptions.map(e => (
              <option key={e.name} value={e.name}>{e.name}</option>
            ))}
          </select>
        )}
      </div>

      {/* Entity info */}
      {entityInfo && (
        <div style={{
          padding: '12px 14px', marginBottom: '16px',
          background: '#0f172a', borderRadius: '8px', border: '1px solid #1e293b',
          animation: 'mb-fadein 0.2s ease',
        }}>
          <p style={{ color: '#94a3b8', fontSize: '12px', margin: '0 0 8px' }}>{entityInfo.description}</p>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {mandatoryFields.map(f => (
              <span key={f.name} style={{
                padding: '2px 8px', borderRadius: '6px', fontSize: '10px',
                background: '#7f1d1d', color: '#fca5a5', border: '1px solid #991b1b',
                fontFamily: 'monospace',
              }}>
                {f.name} <span style={{ opacity: 0.6 }}>({f.type})</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Entries */}
      {entityType && mandatoryFields.length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase' }}>
              Instances ({entries.length})
            </span>
            <button
              onClick={addEntry}
              style={{
                padding: '4px 12px', borderRadius: '6px', border: '1px solid #334155',
                background: '#1e293b', color: '#e2e8f0', fontSize: '11px', cursor: 'pointer',
              }}
            >
              + Add Row
            </button>
          </div>

          {entries.map((entry, idx) => (
            <div key={idx} style={{
              display: 'flex', gap: '8px', marginBottom: '6px', alignItems: 'center',
              padding: '8px 10px', background: idx % 2 === 0 ? '#0f172a' : '#1a2332',
              borderRadius: '8px', border: '1px solid #1e293b',
            }}>
              {mandatoryFields.map(f => (
                <div key={f.name} style={{ flex: 1 }}>
                  <div style={{ color: '#64748b', fontSize: '10px', marginBottom: '2px', fontFamily: 'monospace' }}>
                    {f.name}
                  </div>
                  <input
                    value={entry[f.name] || ''}
                    onChange={e => updateEntry(idx, f.name, e.target.value)}
                    placeholder={f.name === 'identifier' ? 'e.g. RC-001' : 'e.g. Machine Class'}
                    style={{
                      width: '100%', padding: '6px 8px',
                      background: '#1e293b', border: '1px solid #334155', borderRadius: '6px',
                      color: '#f1f5f9', fontSize: '13px', fontFamily: 'monospace',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>
              ))}
              {entries.length > 1 && (
                <button
                  onClick={() => removeEntry(idx)}
                  style={{
                    padding: '4px 8px', borderRadius: '6px', border: '1px solid #7f1d1d',
                    background: 'transparent', color: '#fca5a5', fontSize: '11px', cursor: 'pointer',
                    alignSelf: 'flex-end', marginBottom: '1px',
                  }}
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Save */}
      {entityType && (
        <div>
          <button
            onClick={handleSave}
            disabled={!canSave || saving}
            style={{
              padding: '9px 20px', borderRadius: '8px', border: 'none',
              background: canSave ? 'linear-gradient(135deg, #4c1d95, #6366f1)' : '#1e293b',
              color: canSave ? '#e0e7ff' : '#64748b',
              fontSize: '13px', fontWeight: 600, cursor: canSave ? 'pointer' : 'not-allowed',
              opacity: saving ? 0.7 : 1,
            }}
          >
            {saving ? 'Saving…' : `Create Manual ${entityType}${entries.length > 1 ? ` (${entries.length} instances)` : ''}`}
          </button>

          {feedback && (
            <div style={{
              marginTop: '10px', padding: '8px 14px', borderRadius: '8px',
              background: feedback.type === 'success' ? '#14532d' : '#7f1d1d',
              border: `1px solid ${feedback.type === 'success' ? '#166534' : '#991b1b'}`,
              color: feedback.type === 'success' ? '#86efac' : '#fca5a5',
              fontSize: '12px',
            }}>
              {feedback.message}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
