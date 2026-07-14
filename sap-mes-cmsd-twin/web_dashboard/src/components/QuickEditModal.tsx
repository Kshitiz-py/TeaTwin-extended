import { useState } from 'react';

interface QuickEditModalProps {
  mapping: any;  // full mapping JSON from GET /mappings/{id}
  onClose: () => void;
  onSave: (id: string, changes: Record<string, any>) => void;
}

const TRANSFORM_OPTIONS = [
  { value: 'none', label: 'None' },
  { value: 'unit_conversion', label: 'Unit Conversion' },
  { value: 'enum_map', label: 'Enum Map' },
  { value: 'to_decimal', label: 'To Decimal' },
  { value: 'to_integer', label: 'To Integer' },
  { value: 'string_template', label: 'String Template' },
  { value: 'divide_by', label: 'Divide By' },
  { value: 'multiply_by', label: 'Multiply By' },
  { value: 'default_value', label: 'Default Value' },
];

export default function QuickEditModal({ mapping, onClose, onSave }: QuickEditModalProps) {
  const fieldMap = mapping?.mapping || {};
  const fieldNames = Object.keys(fieldMap);
  const mappingId = mapping?.id || mapping?._id || '';

  const [edits, setEdits] = useState<Record<string, { type: string; params: string }>>(() => {
    const initial: Record<string, { type: string; params: string }> = {};
    for (const [field, config] of Object.entries(fieldMap)) {
      if (typeof config === 'object' && config) {
        const t = (config as any).transformation;
        initial[field] = {
          type: t?.type || 'none',
          params: t?.params ? JSON.stringify(t.params) : '{}',
        };
      }
    }
    return initial;
  });

  const handleSave = () => {
    const changes: Record<string, any> = {};
    for (const [field, edit] of Object.entries(edits)) {
      if (edit.type === 'none') {
        changes[field] = { ...(fieldMap[field] as any || {}), transformation: null };
      } else {
        let params = {};
        try { params = JSON.parse(edit.params); } catch {}
        changes[field] = { ...(fieldMap[field] as any || {}), transformation: { type: edit.type, params } };
      }
    }
    onSave(mappingId, { mapping: { ...fieldMap, ...changes } });
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.7)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }}>
      <div style={{
        background: '#1e293b', borderRadius: '12px', border: '1px solid #334155',
        padding: '24px', width: '700px', maxHeight: '85vh', overflow: 'auto',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ color: '#f1f5f9', margin: 0, fontSize: '16px' }}>
              Quick Edit — {mapping?.data_point || mapping?.data_point_name || 'Mapping'}
            </h3>
            <p style={{ color: '#94a3b8', fontSize: '12px', margin: '4px 0 0' }}>
              {mapping?.cmsd_entity} · {fieldNames.length} fields
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              width: '28px', height: '28px', borderRadius: '6px', border: '1px solid #334155',
              background: 'transparent', color: '#94a3b8', fontSize: '14px', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', lineHeight: 1,
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#334155'; e.currentTarget.style.color = '#f1f5f9'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94a3b8'; }}
          >✕</button>
        </div>

        {fieldNames.length === 0 ? (
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>No fields in this mapping.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', padding: '6px 10px' }}>
              <span style={{ color: '#64748b', fontSize: '11px', fontWeight: 600 }}>CMSD Field</span>
              <span style={{ color: '#64748b', fontSize: '11px', fontWeight: 600 }}>Transform</span>
              <span style={{ color: '#64748b', fontSize: '11px', fontWeight: 600 }}>Params</span>
            </div>
            {fieldNames.map(field => {
              const config = fieldMap[field] as any || {};
              const apiPath = config?.api_path || '';
              const edit = edits[field] || { type: 'none', params: '{}' };
              return (
                <div key={field} style={{
                  display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px',
                  padding: '8px 10px', background: '#0f172a', borderRadius: '6px',
                  border: '1px solid #1e293b', alignItems: 'center',
                }}>
                  <div>
                    <span style={{ color: '#e2e8f0', fontSize: '12px', fontWeight: 600 }}>{field}</span>
                    {apiPath && (
                      <span style={{ color: '#64748b', fontSize: '10px', display: 'block', fontFamily: 'monospace' }}>
                        {apiPath}
                      </span>
                    )}
                  </div>
                  <select
                    value={edit.type}
                    onChange={(e) => setEdits(prev => ({
                      ...prev, [field]: { ...prev[field], type: e.target.value },
                    }))}
                    style={{
                      padding: '4px 6px', borderRadius: '4px', fontSize: '11px',
                      background: '#1e293b', border: '1px solid #475569', color: '#e2e8f0',
                    }}
                  >
                    {TRANSFORM_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                  <input
                    value={edit.params}
                    onChange={(e) => setEdits(prev => ({
                      ...prev, [field]: { ...prev[field], params: e.target.value },
                    }))}
                    disabled={edit.type === 'none'}
                    placeholder='{"key": "value"}'
                    style={{
                      padding: '4px 6px', borderRadius: '4px', fontSize: '11px', fontFamily: 'monospace',
                      background: edit.type === 'none' ? '#0f172a' : '#1e293b',
                      border: '1px solid #475569', color: edit.type === 'none' ? '#475569' : '#e2e8f0',
                    }}
                  />
                </div>
              );
            })}
          </div>
        )}

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={{
            padding: '8px 16px', borderRadius: '6px', background: '#334155',
            border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '13px',
          }}>
            Cancel
          </button>
          <button onClick={handleSave} style={{
            padding: '8px 16px', borderRadius: '6px', background: '#065f46',
            border: 'none', color: '#6ee7b7', cursor: 'pointer', fontSize: '13px', fontWeight: 600,
          }}>
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
