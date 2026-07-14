import { useMemo, useEffect, useState } from 'react';

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
  changedFields?: Set<string>;
  instanceData?: Record<string, any>;
}

const highlightKeyframes = `
@keyframes field-highlight {
  0% { background: rgba(59, 130, 246, 0.3); }
  100% { background: transparent; }
}
`;

function getValueAtPath(obj: Record<string, any>, path: string): any {
  if (!path) return undefined;
  const parts = path.split('.');
  let current: any = obj;
  for (const part of parts) {
    if (current === null || current === undefined) return undefined;
    if (typeof current === 'object' && part in current) {
      current = current[part];
    } else {
      return undefined;
    }
  }
  return current;
}

function stripArrayPrefix(apiPath: string, countPath: string): string {
  if (!countPath || !apiPath) return apiPath;
  let cleanPath = apiPath.replace(/^\$\./, '');
  const cleaned = countPath.replace(/^\$\./, '').replace(/\[[*]\]$/, '');
  const parts = cleaned.split('.').filter(Boolean);
  const arrayPrefix = parts.join('.');
  if (!arrayPrefix) return cleanPath;
  const patterns = [arrayPrefix + '.', arrayPrefix + '[*].', arrayPrefix + '['];
  for (const pat of patterns) {
    if (cleanPath.startsWith(pat)) {
      let rest = cleanPath.slice(pat.length);
      rest = rest.replace(/^(\d+|\[[*]\])\./, '');
      return rest || cleanPath;
    }
  }
  const segments = cleanPath.split('.');
  const clean = segments.filter(s => s !== '' && !/^\d+$/.test(s) && s !== '[*]');
  const prefixSegs = arrayPrefix.split('.');
  let startIdx = 0;
  while (startIdx < prefixSegs.length && startIdx < clean.length && clean[startIdx] === prefixSegs[startIdx]) {
    startIdx++;
  }
  if (startIdx > 0 && startIdx < clean.length) {
    return clean.slice(startIdx).join('.');
  }
  return cleanPath;
}

function expandPaths(fields: Record<string, FieldMapping>, instanceData?: Record<string, any>, countPath?: string): any {
  const result: any = {};

  for (const [cmsdField, info] of Object.entries(fields)) {
    const parts = cmsdField.split('.');
    let current = result;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!current[parts[i]]) current[parts[i]] = {};
      current = current[parts[i]];
    }
    const leaf = parts[parts.length - 1];

    // Use actual instance value if available, otherwise fall back to mapping sample
    let displayValue = info.converted_value || info.raw_value || '';
    if (instanceData && info.api_path) {
      let actual = getValueAtPath(instanceData, info.api_path);
      if (actual === undefined && countPath) {
        const relative = stripArrayPrefix(info.api_path, countPath);
        if (relative !== info.api_path) {
          actual = getValueAtPath(instanceData, relative);
        }
      }
      if (actual !== undefined && actual !== null) {
        displayValue = typeof actual === 'object' ? JSON.stringify(actual) : String(actual);
      }
    }

    current[leaf] = {
      value: displayValue,
      source: info.source_endpoint || '',
      apiPath: info.api_path,
      confidence: info.confidence || '',
    };
  }

  return result;
}

function renderJsonNode(obj: any, depth: number = 0, changedFields?: Set<string>, pathPrefix?: string): JSX.Element {
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
            {renderJsonNode(item, depth + 1, changedFields, pathPrefix)}
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
        const fieldPath = pathPrefix ? `${pathPrefix}.${key}` : key;
        const isChanged = changedFields?.has(fieldPath);
        const isManual = isLeaf && val.confidence === 'manual';

        return (
          <span key={key}>
            {i > 0 && <span style={{ color: '#94a3b8' }}>,{'\n'}</span>}
            <span
              style={{
                whiteSpace: 'pre',
                animation: isChanged ? 'field-highlight 1.5s ease-out' : undefined,
                display: 'inline-block',
                borderRadius: '3px',
                padding: isChanged ? '0 4px' : undefined,
              }}
            >
              {childIndent}
            </span>
            <span style={{ color: '#c4b5fd' }}>"{key}"</span>
            <span style={{ color: '#94a3b8' }}>: </span>
            {isLeaf
              ? (
                <span style={{
                  animation: isChanged ? 'field-highlight 1.5s ease-out' : undefined,
                  borderRadius: '3px', padding: isChanged ? '0 4px' : undefined,
                }}>
                  {renderJsonNode(val.value, depth + 1, changedFields, fieldPath)}
                  {isManual && (
                    <span style={{
                      marginLeft: '6px', fontSize: '9px', color: '#93c5fd',
                      background: '#1e3a5f', padding: '1px 5px', borderRadius: '8px',
                      fontWeight: 600, verticalAlign: 'middle',
                    }}>
                      manual
                    </span>
                  )}
                </span>
              )
              : renderJsonNode(val, depth + 1, changedFields, fieldPath)
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

export default function EntityPreview({ mapping, cmsdEntity, instances, changedFields, instanceData }: Props) {
  const [animFields, setAnimFields] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (changedFields && changedFields.size > 0) {
      setAnimFields(new Set(changedFields));
      const timer = setTimeout(() => setAnimFields(new Set()), 1600);
      return () => clearTimeout(timer);
    }
  }, [changedFields]);

  const expanded = useMemo(() => {
    const fields = mapping?.mapping ?? {};
    return expandPaths(fields, instanceData, instances?.count_path);
  }, [mapping, instanceData, instances?.count_path]);

  const fields = mapping?.mapping ?? {};
  const fieldCount = Object.keys(fields).length;

  if (fieldCount === 0) {
    return null;
  }

  const manualCount = Object.values(fields).filter(f => f.confidence === 'manual').length;
  const hasInstanceData = instanceData && Object.keys(instanceData).length > 0;

  return (
    <div style={{ marginBottom: '16px' }}>
      <style>{highlightKeyframes}</style>
      <h4 style={{
        color: '#f1f5f9', margin: '0 0 10px', fontSize: '15px',
        fontWeight: 600,
      }}>
        Entity Preview — {cmsdEntity}
        {hasInstanceData && (
          <span style={{ fontSize: '12px', color: '#86efac', fontWeight: 400, marginLeft: '8px' }}>
            (live instance)
          </span>
        )}
        {!hasInstanceData && instances?.count_path && (
          <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 400, marginLeft: '8px' }}>
            (sample of one entity)
          </span>
        )}
        {manualCount > 0 && (
          <span style={{
            marginLeft: '8px', fontSize: '10px', color: '#93c5fd',
            background: '#1e3a5f', padding: '2px 8px', borderRadius: '8px',
            fontWeight: 600, verticalAlign: 'middle',
          }}>
            {manualCount} manual
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
          {renderJsonNode(expanded, 0, animFields)}
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
