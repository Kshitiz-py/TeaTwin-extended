interface FieldMapping {
  api_path: string;
  type_conversion: string;
  raw_value: string;
  converted_value: string;
  sample_value: string;
  confidence: string;
  source_endpoint?: string;
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
}

const CONFIDENCE_COLORS: Record<string, { bg: string; fg: string; label: string }> = {
  high: { bg: '#14532d', fg: '#86efac', label: 'High' },
  medium: { bg: '#713f12', fg: '#fde68a', label: 'Medium' },
  low: { bg: '#7f1d1d', fg: '#fca5a5', label: 'Low' },
  manual: { bg: '#1e3a5f', fg: '#93c5fd', label: 'Manual' },
};

export default function MappingTable({ mapping, cmsdEntity }: Props) {
  const fields = mapping?.mapping ?? {};
  const fieldNames = Object.keys(fields);

  if (fieldNames.length === 0) {
    return (
      <div style={{
        padding: '24px', textAlign: 'center', color: '#94a3b8',
        background: '#1e293b', borderRadius: '8px', border: '1px solid #334155',
        fontSize: '13px', marginBottom: '16px',
      }}>
        No field mappings proposed for <strong>{cmsdEntity}</strong>.
      </div>
    );
  }

  return (
    <div style={{ marginBottom: '16px' }}>
      <h4 style={{
        color: '#f1f5f9', margin: '0 0 ' + '10px', fontSize: '15px',
        fontWeight: 600,
      }}>
        Proposed Field Mapping — {cmsdEntity}
      </h4>

      <div style={{ overflowX: 'auto', borderRadius: '8px', border: '1px solid #334155' }}>
        <table style={{
          width: '100%', borderCollapse: 'collapse',
          fontSize: '13px', color: '#e2e8f0',
        }}>
          <thead>
            <tr style={{ background: '#1e293b' }}>
              <th style={thStyle}>CMSD Field</th>
              <th style={thStyle}>API Path</th>
              <th style={thStyle}>Source Endpoint</th>
              <th style={thStyle}>Raw Value</th>
              <th style={thStyle}>Converted Value</th>
              <th style={{ ...thStyle, textAlign: 'center' }}>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {fieldNames.map(fieldName => {
              const f: FieldMapping = fields[fieldName];
              const conf = CONFIDENCE_COLORS[f.confidence] || CONFIDENCE_COLORS.medium;

              return (
                <tr
                  key={fieldName}
                  style={{
                    borderTop: '1px solid #334155',
                    background: '#0f172a',
                  }}
                >
                  <td style={tdStyle}>
                    <code style={{
                      color: '#c4b5fd', background: '#1e293b',
                      padding: '2px 6px', borderRadius: '3px', fontSize: '12px',
                      fontWeight: 600,
                    }}>
                      {fieldName}
                    </code>
                  </td>
                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: '12px', color: '#93c5fd' }}>
                    {f.api_path || <span style={{ color: '#64748b' }}>—</span>}
                  </td>
                  <td style={tdStyle}>
                    {f.source_endpoint ? (
                      <span style={{
                        color: '#f1f5f9', background: '#1e3a5f',
                        padding: '2px 8px', borderRadius: '4px', fontSize: '12px',
                      }}>
                        {f.source_endpoint}
                      </span>
                    ) : (
                      <span style={{ color: '#64748b' }}>—</span>
                    )}
                  </td>
                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: '12px', maxWidth: '180px' }}>
                    <div style={{
                      overflow: 'hidden', textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap', color: '#f1f5f9',
                    }} title={String(f.raw_value)}>
                      {f.raw_value || <span style={{ color: '#64748b' }}>—</span>}
                    </div>
                  </td>
                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: '12px', maxWidth: '180px' }}>
                    <div style={{
                      overflow: 'hidden', textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap', color: '#86efac',
                    }} title={String(f.converted_value)}>
                      {f.converted_value || <span style={{ color: '#64748b' }}>—</span>}
                    </div>
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'center' }}>
                    <span style={{
                      display: 'inline-block', padding: '3px 10px',
                      borderRadius: '10px', fontSize: '11px', fontWeight: 600,
                      background: conf.bg, color: conf.fg,
                    }}>
                      {conf.label}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Unmapped fields shown in table footer */}
      {mapping?.unmapped_fields && mapping.unmapped_fields.length > 0 && (
        <div style={{
          marginTop: '10px', padding: '10px 14px', background: '#422006',
          borderRadius: '6px', border: '1px solid #f59e0b',
          fontSize: '12px', color: '#fde68a',
        }}>
          <strong>Unmapped CMSD fields:</strong>{' '}
          {mapping.unmapped_fields.map(f => (
            <code key={f} style={{
              color: '#fde68a', background: '#78350f',
              padding: '1px 6px', borderRadius: '3px', margin: '0 3px',
              fontSize: '11px',
            }}>
              {f}
            </code>
          ))}
        </div>
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = {
  padding: '10px 12px', textAlign: 'left',
  fontSize: '11px', fontWeight: 600, color: '#94a3b8',
  textTransform: 'uppercase', letterSpacing: '0.5px',
  borderBottom: '2px solid #334155',
};

const tdStyle: React.CSSProperties = {
  padding: '10px 12px',
  verticalAlign: 'middle',
};
