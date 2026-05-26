import { useMemo } from 'react';

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
  mapping?: Record<string, FieldMapping>;
  [key: string]: any;
}

interface Props {
  mapping: MappingData | null;
  cmsdEntity: string;
  instances?: { count_path?: string; key_field?: string };
}

/**
 * Expand dot-notation paths into a nested object.
 * e.g., {"size.width": {converted_value: 2.5}} becomes {size: {width: 2.5}}
 */
function expandPaths(fields: Record<string, FieldMapping>): any {
  const result: any = {};

  for (const [cmsdField, info] of Object.entries(fields)) {
    const parts = cmsdField.split('.');
    let current = result;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!current[parts[i]]) current[parts[i]] = {};
      current = current[parts[i]];
    }
    const leaf = parts[parts.length - 1];
    current[leaf] = {
      value: info.converted_value || info.raw_value || '',
      source: info.source_endpoint || '',
      apiPath: info.api_path,
    };
  }

  return result;
}

function renderJsonNode(obj: any, depth: number = 0): JSX.Element {
  if (obj === null || obj === undefined) {
    return <span style={{ color: '#64748b' }}>null</span>;
  }

  if (typeof obj === 'string') {
    return <span style={{ color: '#86efac' }}>"{obj}"</span>;
  }

  if (typeof obj === 'number') {
    return <span style={{ color: '#93c5fd' }}>{obj}</span>;
  }

  if (typeof obj === 'boolean') {
    return <span style={{ color: '#fde68a' }}>{String(obj)}</span>;
  }

  if (Array.isArray(obj)) {
    if (obj.length === 0) return <span style={{ color: '#94a3b8' }}>[]</span>;
    return (
      <span>
        <span style={{ color: '#94a3b8' }}>[</span>
        {obj.map((item, i) => (
          <span key={i}>
            {i > 0 && <span style={{ color: '#94a3b8' }}>, </span>}
            {renderJsonNode(item, depth + 1)}
          </span>
        ))}
        <span style={{ color: '#94a3b8' }}>]</span>
      </span>
    );
  }

  const keys = Object.keys(obj);
  if (keys.length === 0) return <span style={{ color: '#94a3b8' }}>{'{}'}</span>;

  const indent = '  '.repeat(depth);
  const childIndent = '  '.repeat(depth + 1);

  return (
    <span>
      <span style={{ color: '#94a3b8' }}>{'{'}</span>
      {'\n'}
      {keys.map((key, i) => {
        const val = obj[key];
        const isLeaf = val && typeof val === 'object' && 'value' in val;

        return (
          <span key={key}>
            {i > 0 && <span style={{ color: '#94a3b8' }}>,{'\n'}</span>}
            <span style={{ whiteSpace: 'pre' }}>{childIndent}</span>
            <span style={{ color: '#c4b5fd' }}>"{key}"</span>
            <span style={{ color: '#94a3b8' }}>: </span>
            {isLeaf
              ? renderJsonNode(val.value, depth + 1)
              : renderJsonNode(val, depth + 1)
            }
          </span>
        );
      })}
      {'\n'}
      <span style={{ whiteSpace: 'pre' }}>{indent}</span>
      <span style={{ color: '#94a3b8' }}>{'}'}</span>
    </span>
  );
}

export default function EntityPreview({ mapping, cmsdEntity, instances }: Props) {
  const expanded = useMemo(() => {
    const fields = mapping?.mapping ?? {};
    return expandPaths(fields);
  }, [mapping]);

  const fields = mapping?.mapping ?? {};
  const fieldCount = Object.keys(fields).length;

  if (fieldCount === 0) {
    return null;
  }

  return (
    <div style={{ marginBottom: '16px' }}>
      <h4 style={{
        color: '#f1f5f9', margin: '0 0 10px', fontSize: '15px',
        fontWeight: 600,
      }}>
        Entity Preview — {cmsdEntity}
        {instances?.count_path && (
          <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 400, marginLeft: '8px' }}>
            (sample of one entity)
          </span>
        )}
      </h4>

      <div style={{
        background: '#0f172a', borderRadius: '8px',
        border: '1px solid #334155', padding: '16px',
        maxHeight: '400px', overflow: 'auto',
      }}>
        <pre style={{
          margin: 0, fontSize: '13px', lineHeight: 1.7,
          fontFamily: '"Fira Code", "Cascadia Code", "JetBrains Mono", monospace',
          color: '#e2e8f0', whiteSpace: 'pre',
        }}>
          {renderJsonNode(expanded)}
        </pre>
      </div>

      {/* Source legend */}
      <div style={{
        marginTop: '8px', display: 'flex', gap: '16px', flexWrap: 'wrap',
      }}>
        {Object.entries(fields).map(([fieldName, info]) => (
          info.source_endpoint ? (
            <div key={fieldName} style={{
              fontSize: '11px', color: '#94a3b8',
              display: 'flex', alignItems: 'center', gap: '4px',
            }}>
              <code style={{
                color: '#c4b5fd', background: '#1e293b',
                padding: '1px 4px', borderRadius: '2px', fontSize: '10px',
              }}>
                {fieldName}
              </code>
              <span style={{ color: '#64748b' }}>←</span>
              <span style={{ color: '#93c5fd' }}>{info.source_endpoint}</span>
            </div>
          ) : null
        ))}
      </div>
    </div>
  );
}
