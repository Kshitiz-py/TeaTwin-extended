import { useState } from 'react';

interface MappingField {
  api_path: string;
  type_conversion: string;
  sample_value: string;
  raw_value?: string;
  converted_value?: string;
  confidence: string;
}

interface FieldMappingTableProps {
  mapping: Record<string, MappingField>;
  cmsdEntity: string;
  unmappedFields: string[];
  onEdit: (field: string, updates: Partial<MappingField>) => void;
  onRemove: (field: string) => void;
  onConfirm: () => void;
  onReanalyze: () => void;
  onSmartReanalyze?: (guidance: string) => void;
  isConfirmed: boolean;
  isGenerating: boolean;
}

const confidenceColor = (c: string) => {
  switch (c) {
    case 'high': return { bg: '#064e3b', text: '#4ade80' };
    case 'medium': return { bg: '#78350f', text: '#fbbf24' };
    case 'low': return { bg: '#7f1d1d', text: '#fca5a5' };
    case 'manual': return { bg: '#1e3a5f', text: '#93c5fd' };
    default: return { bg: '#334155', text: '#94a3b8' };
  }
};

export default function FieldMappingTable({
  mapping, cmsdEntity, unmappedFields, onEdit, onRemove, onConfirm, onReanalyze, onSmartReanalyze, isConfirmed, isGenerating,
}: FieldMappingTableProps) {
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<Partial<MappingField>>({});
  const [savedFeedback, setSavedFeedback] = useState<string | null>(null);
  const [guidanceInput, setGuidanceInput] = useState('');
  const [guidanceOpen, setGuidanceOpen] = useState(false);
  const fields = Object.entries(mapping);

  const startEdit = (field: string, current: MappingField) => {
    setEditingField(field);
    setEditValues({ ...current });
  };

  const saveEdit = () => {
    if (editingField) {
      onEdit(editingField, { ...editValues, confidence: 'manual' });
      setEditingField(null);
      setEditValues({});
      setSavedFeedback(editingField);
      setTimeout(() => setSavedFeedback(null), 1500);
    }
  };

  const cancelEdit = () => {
    setEditingField(null);
    setEditValues({});
  };

  const handleGuidanceReanalyze = () => {
    const g = guidanceInput.trim();
    if (g && onSmartReanalyze) {
      onSmartReanalyze(g);
      setGuidanceOpen(false);
      setGuidanceInput('');
    }
  };

  return (
    <div>
      {/* Unmapped fields warning */}
      {unmappedFields.length > 0 && (
        <div style={{ padding: '10px 14px', background: '#78350f', borderRadius: '6px', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '16px' }}>⚠️</span>
          <div>
            <p style={{ color: '#fbbf24', fontSize: '13px', fontWeight: 600, margin: 0 }}>Unmapped Required Fields</p>
            <p style={{ color: '#fcd34d', fontSize: '11px', margin: '2px 0 0' }}>
              {unmappedFields.join(', ')}
            </p>
          </div>
        </div>
      )}

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', minWidth: '780px' }}>
          <thead>
            <tr style={{ background: '#0f172a' }}>
              <th style={th}>CMSD Field</th>
              <th style={th}>API Path</th>
              <th style={th}>Raw Value</th>
              <th style={th}>Conversion</th>
              <th style={th}>Converted</th>
              <th style={th}>Confidence</th>
              <th style={th}></th>
            </tr>
          </thead>
          <tbody>
            {fields.map(([field, info]) => {
              const isEditing = editingField === field;
              const isSaved = savedFeedback === field;
              return (
                <tr key={field} style={{ borderBottom: '1px solid #334155', background: isEditing ? '#1e293b' : isSaved ? 'rgba(34,197,94,0.08)' : 'transparent', transition: 'background 0.3s' }}>
                  <td style={td}><span style={{ color: '#f1f5f9', fontWeight: 500 }}>{field}</span></td>
                  <td style={td}>
                    {isEditing ? (
                      <input value={editValues.api_path || ''} onChange={e => setEditValues(prev => ({ ...prev, api_path: e.target.value }))}
                        style={inputStyle} />
                    ) : (
                      <span style={{ color: '#94a3b8', fontFamily: 'monospace', fontSize: '11px' }}>{info.api_path}</span>
                    )}
                  </td>
                  <td style={td}>
                    <span style={{ color: '#64748b', fontSize: '11px', fontFamily: 'monospace', maxWidth: '120px', display: 'inline-block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {info.raw_value || info.sample_value || '—'}
                    </span>
                  </td>
                  <td style={td}>
                    {isEditing ? (
                      <select value={editValues.type_conversion || 'none'} onChange={e => setEditValues(prev => ({ ...prev, type_conversion: e.target.value }))}
                        style={{ ...inputStyle, width: '100%' }}>
                        {['none', 'to_decimal', 'to_duration', 'to_weight', 'to_dimensions'].map(o => <option key={o} value={o}>{o}</option>)}
                      </select>
                    ) : (
                      <span style={{ color: '#94a3b8', fontSize: '10px' }}>{info.type_conversion || 'none'}</span>
                    )}
                  </td>
                  <td style={td}>
                    {info.converted_value ? (
                      <span style={{ color: '#4ade80', fontSize: '11px', fontFamily: 'monospace' }}>{info.converted_value}</span>
                    ) : info.type_conversion && info.type_conversion !== 'none' ? (
                      <span style={{ color: '#fbbf24', fontSize: '10px', fontStyle: 'italic' }}>(converted)</span>
                    ) : (
                      <span style={{ color: '#64748b', fontSize: '11px' }}>—</span>
                    )}
                  </td>
                  <td style={td}>
                    <span style={{
                      padding: '2px 8px', borderRadius: '10px', fontSize: '11px', fontWeight: 600,
                      background: confidenceColor(info.confidence).bg,
                      color: confidenceColor(info.confidence).text,
                    }}>{info.confidence}</span>
                  </td>
                  <td style={td}>
                    {isEditing ? (
                      <>
                        <button onClick={saveEdit} style={actionBtn('#22c55e')} title="Save">💾</button>
                        <button onClick={cancelEdit} style={actionBtn('#64748b')} title="Cancel">✖</button>
                      </>
                    ) : (
                      <>
                        <button onClick={() => startEdit(field, info)} style={actionBtn('#3b82f6')} title="Edit">✏️</button>
                        <button onClick={() => onRemove(field)} style={actionBtn('#ef4444')} title="Remove">×</button>
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {fields.length === 0 && (
        <div style={{ textAlign: 'center', padding: '32px', color: '#64748b', fontSize: '14px' }}>
          No mapping fields yet. Analyze an API endpoint first.
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: '10px', marginTop: '16px', justifyContent: 'flex-end', flexWrap: 'wrap', alignItems: 'center' }}>
        {isGenerating ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', background: '#1e3a5f', borderRadius: '6px', color: '#93c5fd', fontSize: '14px' }}>
            <span>⏳</span> Generating code...
          </div>
        ) : (
          <>
            <button onClick={onReanalyze} disabled={isGenerating}
              style={{ padding: '10px 20px', background: '#334155', color: '#94a3b8', border: '1px solid #475569', borderRadius: '6px', cursor: 'pointer', fontSize: '13px' }}>
              🔄 Re-analyze
            </button>
            {guidanceOpen ? (
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flex: 1, minWidth: '280px' }}>
                <input
                  value={guidanceInput}
                  onChange={e => setGuidanceInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleGuidanceReanalyze(); if (e.key === 'Escape') setGuidanceOpen(false); }}
                  placeholder="e.g., MTTR should come from /incidents API..."
                  style={{ flex: 1, background: '#0f172a', border: '1px solid #475569', borderRadius: '6px', padding: '8px 10px', color: '#f1f5f9', fontSize: '12px' }}
                  autoFocus
                />
                <button onClick={handleGuidanceReanalyze}
                  style={{ padding: '8px 14px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 500, whiteSpace: 'nowrap' }}>
                  🎯 Apply
                </button>
                <button onClick={() => { setGuidanceOpen(false); setGuidanceInput(''); }}
                  style={{ padding: '8px 10px', background: '#334155', color: '#94a3b8', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>
                  ✖
                </button>
              </div>
            ) : (
              <button onClick={() => setGuidanceOpen(true)}
                style={{ padding: '10px 20px', background: '#1e3a5f', color: '#93c5fd', border: '1px solid #475569', borderRadius: '6px', cursor: 'pointer', fontSize: '13px' }}>
                🧠 Re-analyze with Guidance
              </button>
            )}
            {!isConfirmed && (
              <button onClick={onConfirm} disabled={fields.length === 0 || unmappedFields.length > 0}
                style={{
                  padding: '10px 24px', borderRadius: '6px', border: 'none', cursor: (fields.length === 0 || unmappedFields.length > 0) ? 'not-allowed' : 'pointer',
                  background: (fields.length === 0 || unmappedFields.length > 0) ? '#334155' : '#22c55e',
                  color: (fields.length === 0 || unmappedFields.length > 0) ? '#64748b' : '#fff',
                  fontSize: '14px', fontWeight: 600,
                }}>
                ✅ Confirm & Generate Code
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

const th: React.CSSProperties = { padding: '8px 8px', textAlign: 'left', color: '#94a3b8', fontSize: '10px', textTransform: 'uppercase', fontWeight: 600, whiteSpace: 'nowrap' };
const td: React.CSSProperties = { padding: '8px' };
const inputStyle: React.CSSProperties = { background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '4px 8px', color: '#f1f5f9', fontSize: '12px', width: '100%', boxSizing: 'border-box' };
const actionBtn = (color: string): React.CSSProperties => ({ background: 'none', border: 'none', color, cursor: 'pointer', fontSize: '16px', padding: '2px 4px', marginLeft: '2px' });