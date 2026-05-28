import React, { useState, useCallback, useRef, useEffect } from 'react';
import TransformSelector, { TransformConfig } from './TransformSelector';
import { agentApi } from '../services/agentApi';

interface FieldMapping {
  api_path: string;
  type_conversion: string;
  raw_value: string;
  converted_value: string;
  sample_value: string;
  confidence: string;
  source_endpoint?: string;
  transformation?: TransformConfig | null;
}

interface MappingData {
  data_point?: string;
  cmsd_entity?: string;
  api_endpoint?: string;
  mapping?: Record<string, FieldMapping>;
  unmapped_fields?: string[];
  requires_manual_review?: boolean;
  notes?: string;
}

interface Props {
  mapping: MappingData | null;
  cmsdEntity: string;
  availableEndpoints?: string[];
  onMappingChange?: (mapping: MappingData) => void;
  onAddMapping?: (fieldName: string) => void;
  // Review mode
  reviewMode?: boolean;
  fieldStatuses?: Record<string, 'approved' | 'flagged' | 'pending'>;
  fieldComments?: Record<string, string>;
  onStatusChange?: (field: string, status: 'approved' | 'flagged' | 'pending') => void;
  onCommentChange?: (field: string, comment: string) => void;
  // Type validation
  typeValidation?: Record<string, {
    api_path: string; raw_value: any; expected_type: string;
    valid: boolean; error: string; suggestion: string;
    unit_sensitive?: boolean; assumed_unit?: string;
  }> | null;
}

const CONFIDENCE_COLORS: Record<string, { bg: string; fg: string; label: string }> = {
  high: { bg: '#14532d', fg: '#86efac', label: 'High' },
  medium: { bg: '#713f12', fg: '#fde68a', label: 'Medium' },
  low: { bg: '#7f1d1d', fg: '#fca5a5', label: 'Low' },
  manual: { bg: '#1e3a5f', fg: '#93c5fd', label: 'Manual' },
};

const STATUS_STYLES: Record<string, { icon: string; color: string; bg: string; label: string }> = {
  approved: { icon: '✓', color: '#86efac', bg: '#14532d', label: 'Approved' },
  flagged: { icon: '⚑', color: '#fde68a', bg: '#78350f', label: 'Flagged' },
  pending: { icon: '·', color: '#64748b', bg: 'transparent', label: 'Pending' },
};

export default function MappingTable({
  mapping, cmsdEntity, availableEndpoints, onMappingChange, onAddMapping,
  reviewMode, fieldStatuses, fieldComments, onStatusChange, onCommentChange,
  typeValidation,
}: Props) {
  const fields = mapping?.mapping ?? {};
  const fieldNames = Object.keys(fields);
  const [editingApiPath, setEditingApiPath] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [showUnmapped, setShowUnmapped] = useState(false);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [commentDraft, setCommentDraft] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const commentRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (editingApiPath && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingApiPath]);

  useEffect(() => {
    if (expandedRow && commentRef.current) {
      commentRef.current.focus();
    }
  }, [expandedRow]);

  const startEditingApiPath = (fieldName: string) => {
    const f = fields[fieldName];
    setEditValue(f?.api_path || '');
    setEditingApiPath(fieldName);
  };

  const commitApiPath = useCallback(() => {
    if (!editingApiPath || !onMappingChange) { setEditingApiPath(null); return; }
    const current = fields[editingApiPath];
    const updatedMapping = {
      ...mapping,
      mapping: {
        ...fields,
        [editingApiPath]: {
          ...(current || { api_path: '', type_conversion: 'none', raw_value: '', converted_value: '', sample_value: '', confidence: 'manual' }),
          api_path: editValue, confidence: 'manual', source_endpoint: current?.source_endpoint || '',
        },
      },
    };
    onMappingChange(updatedMapping);
    setEditingApiPath(null);
  }, [editingApiPath, editValue, fields, mapping, onMappingChange]);

  const handleSourceChange = (fieldName: string, newSource: string) => {
    if (!onMappingChange) return;
    const current = fields[fieldName];
    onMappingChange({
      ...mapping,
      mapping: {
        ...fields,
        [fieldName]: { ...(current || { api_path: '', type_conversion: 'none', raw_value: '', converted_value: '', sample_value: '', confidence: 'manual' }), source_endpoint: newSource, confidence: 'manual' },
      },
    });
  };

  const handleTransformChange = (fieldName: string, config: TransformConfig | null) => {
    if (!onMappingChange) return;
    const current = fields[fieldName];
    onMappingChange({
      ...mapping,
      mapping: {
        ...fields,
        [fieldName]: { ...(current || { api_path: '', type_conversion: 'none', raw_value: '', converted_value: '', sample_value: '', confidence: 'manual' }), transformation: config, confidence: 'manual' },
      },
    });
  };

  const [applyingTransforms, setApplyingTransforms] = useState<Record<string, boolean>>({});
  const [transformResults, setTransformResults] = useState<Record<string, { converted_value: string | null; error?: string }>>({});

  const handleApplyTransform = useCallback(async (fieldName: string, config: TransformConfig) => {
    if (!onMappingChange) return;
    const current = fields[fieldName];
    const rawVal = current?.raw_value || '';

    setApplyingTransforms(prev => ({ ...prev, [fieldName]: true }));
    try {
      const result = await agentApi.applyTransformation(rawVal, config);
      if (result.success && result.converted_value !== null) {
        onMappingChange({
          ...mapping,
          mapping: {
            ...fields,
            [fieldName]: {
              ...(current || { api_path: '', type_conversion: 'none', raw_value: '', converted_value: '', sample_value: '', confidence: 'manual' }),
              transformation: config,
              converted_value: result.converted_value,
              confidence: 'manual',
            },
          },
        });
        setTransformResults(prev => ({ ...prev, [fieldName]: { converted_value: result.converted_value } }));
      } else {
        setTransformResults(prev => ({ ...prev, [fieldName]: { converted_value: '', error: result.error || 'Transformation failed' } }));
      }
    } catch (e: any) {
      setTransformResults(prev => ({ ...prev, [fieldName]: { converted_value: '', error: e.message } }));
    } finally {
      setApplyingTransforms(prev => ({ ...prev, [fieldName]: false }));
    }
  }, [fields, mapping, onMappingChange]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') commitApiPath();
    if (e.key === 'Escape') setEditingApiPath(null);
  };

  const toggleExpand = (fieldName: string) => {
    if (expandedRow === fieldName) {
      setExpandedRow(null);
    } else {
      setExpandedRow(fieldName);
      setCommentDraft(fieldComments?.[fieldName] || '');
    }
  };

  const saveComment = (fieldName: string) => {
    onCommentChange?.(fieldName, commentDraft);
  };

  if (fieldNames.length === 0) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#94a3b8', background: '#1e293b', borderRadius: '8px', border: '1px solid #334155', fontSize: '13px', marginBottom: '16px' }}>
        No field mappings proposed for <strong>{cmsdEntity}</strong>.
      </div>
    );
  }

  const hasEndpoints = availableEndpoints && availableEndpoints.length > 1;
  const endpoints = availableEndpoints || [];
  const flaggedCount = fieldStatuses ? Object.values(fieldStatuses).filter(s => s === 'flagged').length : 0;

  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <h4 style={{ color: '#f1f5f9', margin: 0, fontSize: '15px', fontWeight: 600 }}>
          Field Mapping — {cmsdEntity}
        </h4>
        <span style={{ fontSize: '11px', color: '#64748b' }}>
          {onMappingChange ? 'Click values to edit • ' : ''}
          {reviewMode ? 'Click ▶ to review each field' : 'changes are live'}
        </span>
      </div>

      <div style={{ overflowX: 'auto', borderRadius: '8px', border: '1px solid #334155' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px', color: '#e2e8f0' }}>
          <thead>
            <tr style={{ background: '#1e293b' }}>
              {reviewMode && <th style={{ ...thStyle, width: '38px', textAlign: 'center' }}></th>}
              <th style={thStyle}>Field</th>
              <th style={thStyle}>API Path</th>
              {hasEndpoints && <th style={thStyle}>Src</th>}
              <th style={{ ...thStyle, width: '90px' }}>Raw</th>
              <th style={{ ...thStyle, width: '90px' }}>Conv</th>
              {typeValidation && <th style={{ ...thStyle, width: '70px', textAlign: 'center' }}>Type</th>}
              <th style={{ ...thStyle, width: '140px' }}>Transform</th>
              <th style={{ ...thStyle, textAlign: 'center', width: '28px' }} title="Confidence"></th>
            </tr>
          </thead>
          <tbody>
            {fieldNames.map(fieldName => {
              const f: FieldMapping = fields[fieldName];
              const isEditing = editingApiPath === fieldName;
              const isExpanded = expandedRow === fieldName;
              const conf = CONFIDENCE_COLORS[f.confidence] || CONFIDENCE_COLORS.medium;
              const status = fieldStatuses?.[fieldName] || 'pending';
              const s = STATUS_STYLES[status];

              return (
                <React.Fragment key={fieldName}>
                <tr style={{ borderTop: '1px solid #334155', background: f.confidence === 'manual' ? '#0f1a2e' : '#0f172a', transition: 'background 0.3s ease' }}>
                  {/* Review: expand arrow + status */}
                  {reviewMode && (
                    <td style={{ ...tdStyle, textAlign: 'center', cursor: 'pointer', whiteSpace: 'nowrap' }} onClick={() => toggleExpand(fieldName)}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '10px', color: '#64748b', transition: 'transform 0.15s', display: 'inline-block', transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)' }}>▶</span>
                        <span title={s.label} style={{ fontSize: '14px', color: s.color, fontWeight: 700, lineHeight: 1 }}>{s.icon}</span>
                      </span>
                    </td>
                  )}

                  <td style={tdStyle}>
                    <code style={{ color: '#c4b5fd', background: '#1e293b', padding: '1px 4px', borderRadius: '3px', fontSize: '10px', fontWeight: 600, whiteSpace: 'nowrap' }}>
                      {fieldName}
                    </code>
                  </td>

                  {/* API Path — click to edit if expand not active */}
                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: '10px' }}>
                    {isEditing ? (
                      <input ref={inputRef} value={editValue} onChange={e => setEditValue(e.target.value)} onBlur={commitApiPath} onKeyDown={handleKeyDown}
                        style={{ width: '100%', background: '#1e293b', border: '1px solid #3b82f6', borderRadius: '3px', padding: '3px 6px', color: '#93c5fd', fontSize: '12px', fontFamily: 'monospace', boxSizing: 'border-box' }} />
                    ) : (
                      <span onClick={() => { if (!reviewMode || expandedRow !== fieldName) { if (onMappingChange) startEditingApiPath(fieldName); } }}
                        title="Click to edit"
                        style={{ color: f.api_path ? '#93c5fd' : '#64748b', cursor: onMappingChange && (!reviewMode || expandedRow !== fieldName) ? 'pointer' : 'default', padding: '2px 4px', borderRadius: '3px', display: 'inline-block' }}
                        onMouseEnter={e => { if (onMappingChange) e.currentTarget.style.background = '#1e293b'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}>
                        {f.api_path || '—'}
                      </span>
                    )}
                  </td>

                  {hasEndpoints && (
                    <td style={tdStyle}>
                      <select value={f.source_endpoint || ''} onChange={e => handleSourceChange(fieldName, e.target.value)} disabled={!onMappingChange}
                        style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '3px', padding: '3px 6px', color: '#f1f5f9', fontSize: '11px', fontFamily: 'monospace' }}>
                        <option value="">—</option>
                        {endpoints.map(ep => <option key={ep} value={ep}>{ep}</option>)}
                      </select>
                    </td>
                  )}

                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: '10px', maxWidth: '90px' }}>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#f1f5f9' }} title={String(f.raw_value)}>
                      {f.raw_value || <span style={{ color: '#64748b' }}>—</span>}
                    </div>
                  </td>

                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: '10px', maxWidth: '90px' }}>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#86efac' }} title={String(f.converted_value)}>
                      {f.converted_value || <span style={{ color: '#64748b' }}>—</span>}
                    </div>
                  </td>

                  {typeValidation && (
                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                      {(() => {
                        const tv = typeValidation[fieldName];
                        if (!tv) return <span style={{ color: '#64748b', fontSize: '10px' }}>—</span>;
                        const tooltip = tv.unit_sensitive
                          ? `Expected unit: ${tv.assumed_unit}\n${tv.valid ? 'Value is coercible — verify unit matches' : tv.error}${tv.suggestion ? '\n' + tv.suggestion : ''}`
                          : tv.valid ? `${tv.expected_type} — valid` : `${tv.expected_type} — ${tv.error}${tv.suggestion ? '\n' + tv.suggestion : ''}`;
                        const icon = !tv.valid ? '✕' : tv.unit_sensitive ? '⚠' : '✓';
                        const color = !tv.valid ? '#ef4444' : tv.unit_sensitive ? '#f59e0b' : '#22c55e';
                        return (
                          <span title={tooltip}
                            style={{
                              display: 'inline-flex', alignItems: 'center', gap: '3px',
                              fontSize: '10px', fontWeight: 600, cursor: 'help', color,
                            }}
                          >
                            {icon} {tv.expected_type}
                          </span>
                        );
                      })()}
                    </td>
                  )}

                  <td style={tdStyle}>
                    <TransformSelector value={f.transformation || null} onChange={(config) => handleTransformChange(fieldName, config)} rawValue={f.raw_value} convertedValue={f.converted_value} onApply={(config) => handleApplyTransform(fieldName, config)} applying={applyingTransforms[fieldName] || false} applyResult={transformResults[fieldName]?.converted_value ?? null} applyError={transformResults[fieldName]?.error ?? null} />
                  </td>

                  <td style={{ ...tdStyle, textAlign: 'center' }} title={`${conf.label} confidence`}>
                    <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: conf.fg }} />
                  </td>
                </tr>
                {/* Expanded review row — inline below the selected row */}
                {isExpanded && reviewMode && (
                  <tr key={`${fieldName}-review`} style={{ background: '#0f1a2e' }}>
                    <td colSpan={7 + (hasEndpoints ? 1 : 0) + (reviewMode ? 1 : 0) + (typeValidation ? 1 : 0)} style={{ padding: '0' }}>
                      <div style={{ padding: '12px 16px', borderTop: '1px solid #1e3a5f', borderBottom: '1px solid #334155' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '10px' }}>
                          <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Review</span>
                          <code style={{ color: '#c4b5fd', background: '#1e293b', padding: '3px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 600 }}>{fieldName}</code>
                          <span style={{ color: '#334155' }}>→</span>
                          <code style={{ color: '#93c5fd', fontSize: '11px', fontFamily: 'monospace' }}>{f.api_path || '(no path)'}</code>
                          {fieldComments?.[fieldName] && (
                            <span style={{ marginLeft: 'auto', fontSize: '11px', color: '#fde68a', background: '#422006', padding: '2px 8px', borderRadius: '3px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={fieldComments[fieldName]}>
                              💬 {fieldComments[fieldName]}
                            </span>
                          )}
                        </div>

                        {/* Status toggles */}
                        <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
                          {(['approved', 'pending', 'flagged'] as const).map(s => {
                            const st = STATUS_STYLES[s];
                            const active = (fieldStatuses?.[fieldName] || 'pending') === s;
                            return (
                              <button key={s} onClick={() => onStatusChange?.(fieldName, s)}
                                style={{
                                  padding: '5px 12px', borderRadius: '5px', border: active ? `2px solid ${st.color}` : '1px solid #334155',
                                  background: active ? st.bg : 'transparent', color: active ? st.color : '#64748b',
                                  cursor: 'pointer', fontSize: '12px', fontWeight: active ? 700 : 500,
                                  display: 'flex', alignItems: 'center', gap: '5px',
                                }}>
                                <span style={{ fontSize: '13px' }}>{st.icon}</span> {st.label}
                              </button>
                            );
                          })}
                        </div>

                        {/* Comment */}
                        <div>
                          <label style={{ fontSize: '11px', color: '#94a3b8', display: 'block', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            Comment {fieldStatuses?.[fieldName] === 'flagged' ? '(required for reanalysis)' : '(optional)'}
                          </label>
                          <textarea ref={commentRef} value={commentDraft} onChange={e => setCommentDraft(e.target.value)}
                            placeholder="e.g. This should map to cycle_time_seconds, not cycle_time. The value is in seconds."
                            rows={2}
                            style={{
                              width: '100%', background: '#0f172a', border: '1px solid #334155',
                              borderRadius: '4px', padding: '8px 10px', color: '#e2e8f0',
                              fontSize: '12px', fontFamily: 'monospace', resize: 'vertical', boxSizing: 'border-box',
                            }} />
                          <button onClick={() => saveComment(fieldName)}
                            style={{ marginTop: '6px', padding: '4px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#1e293b', color: '#93c5fd', cursor: 'pointer', fontSize: '11px', fontWeight: 600 }}>
                            Save Comment
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Unmapped fields */}
      {mapping?.unmapped_fields && mapping.unmapped_fields.length > 0 && (
        <div style={{ marginTop: '10px' }}>
          <button onClick={() => setShowUnmapped(!showUnmapped)}
            style={{ padding: '8px 14px', borderRadius: '6px', border: '1px solid #f59e0b', background: '#422006', color: '#fde68a', cursor: 'pointer', fontSize: '12px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>{showUnmapped ? '▼' : '▶'}</span>
            {mapping.unmapped_fields.length} unmapped field{mapping.unmapped_fields.length !== 1 ? 's' : ''}
          </button>
          {showUnmapped && (
            <div style={{ marginTop: '8px', padding: '10px 14px', background: '#422006', borderRadius: '6px', border: '1px solid #f59e0b', fontSize: '12px', color: '#fde68a' }}>
              {mapping.unmapped_fields.map(f => (
                <div key={f} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', margin: '3px 6px 3px 0' }}>
                  <code style={{ color: '#fde68a', background: '#78350f', padding: '2px 6px', borderRadius: '3px', fontSize: '11px' }}>{f}</code>
                  {onAddMapping && (
                    <button onClick={() => onAddMapping(f)} title="Add mapping for this field"
                      style={{ padding: '1px 6px', borderRadius: '3px', border: '1px solid #f59e0b', background: '#78350f', color: '#fde68a', cursor: 'pointer', fontSize: '10px', fontWeight: 600 }}>
                      + Add
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = {
  padding: '6px 8px', textAlign: 'left', fontSize: '10px', fontWeight: 600, color: '#94a3b8',
  textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '2px solid #334155',
};
const tdStyle: React.CSSProperties = {
  padding: '5px 8px', verticalAlign: 'middle',
};
