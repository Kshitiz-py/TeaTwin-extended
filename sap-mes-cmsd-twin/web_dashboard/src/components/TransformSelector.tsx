import { useState, useRef, useEffect } from 'react';

export interface TransformConfig {
  type: string;
  params: Record<string, string>;
}

const LABELS: Record<string, string> = {
  none: 'None',
  unit_conversion: 'Unit Conv',
  enum_map: 'Enum Map',
  to_decimal: 'To Decimal',
  to_integer: 'To Integer',
  string_template: 'Template',
  divide_by: 'Divide By',
  multiply_by: 'Multiply',
  default_value: 'Default',
};

const PARAMS: Record<string, string[]> = {
  none: [],
  unit_conversion: ['from', 'to', 'factor'],
  enum_map: ['mapping'],
  to_decimal: ['precision'],
  to_integer: [],
  string_template: ['template'],
  divide_by: ['divisor'],
  multiply_by: ['factor'],
  default_value: ['value'],
};

const PARAM_LABELS: Record<string, string> = {
  from: 'From unit', to: 'To unit', factor: 'Factor',
  mapping: 'Mapping (JSON)', precision: 'Decimal places',
  template: 'Template ({value})', divisor: 'Divisor',
  value: 'Default value',
};

interface Props {
  value: TransformConfig | null;
  onChange: (config: TransformConfig | null) => void;
  rawValue?: string;
  convertedValue?: string;
  onApply?: (config: TransformConfig) => void;
  applying?: boolean;
  applyResult?: string | null;
  applyError?: string | null;
}

/** Compact summary of the current transform config */
function summary(config: TransformConfig | null): string {
  if (!config || config.type === 'none') return '';
  const p = config.params || {};
  switch (config.type) {
    case 'unit_conversion': return `×${p.factor || '?'}`;
    case 'divide_by': return `÷${p.divisor || '?'}`;
    case 'multiply_by': return `×${p.factor || '?'}`;
    case 'to_decimal': return `.${p.precision || '?'}f`;
    case 'to_integer': return `int`;
    case 'string_template': return `tpl`;
    case 'enum_map': return `enum`;
    case 'default_value': return `=${p.value || '?'}`;
    default: return '';
  }
}

export default function TransformSelector({ value, onChange, rawValue, convertedValue, onApply, applying, applyResult, applyError }: Props) {
  const currentType = value?.type || 'none';
  const currentParams = value?.params || {};
  const [showParams, setShowParams] = useState(false);
  const popRef = useRef<HTMLDivElement>(null);
  const hasApplied = applyResult != null || (!!convertedValue && convertedValue !== rawValue);

  // Close popover on outside click
  useEffect(() => {
    if (!showParams) return;
    const handler = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) {
        setShowParams(false);
      }
    };
    setTimeout(() => document.addEventListener('click', handler), 0);
    return () => document.removeEventListener('click', handler);
  }, [showParams]);

  const handleTypeChange = (type: string) => {
    if (type === 'none') {
      onChange(null);
      setShowParams(false);
    } else {
      const req = PARAMS[type] || [];
      const params: Record<string, string> = {};
      req.forEach(p => { params[p] = currentParams[p] || ''; });
      onChange({ type, params });
      setShowParams(true); // auto-open so user sees the params form
    }
  };

  const handleParamChange = (param: string, val: string) => {
    if (!value || value.type === 'none') return;
    onChange({ ...value, params: { ...value.params, [param]: val } });
  };

  const requiredParams = PARAMS[currentType] || [];
  const hasAllParams = requiredParams.every(p => currentParams[p]?.trim());

  const hasParamsForm = currentType !== 'none' && requiredParams.length > 0;

  return (
    <div ref={popRef} style={{ fontSize: '10px', position: 'relative', display: 'flex', alignItems: 'center', gap: '4px' }}>
      {/* Dropdown */}
      <select
        value={currentType}
        onChange={e => handleTypeChange(e.target.value)}
        style={{
          flex: 1, background: '#0f172a', border: '1px solid #334155',
          borderRadius: '3px', padding: '2px 4px', color: '#e2e8f0',
          fontSize: '10px', fontFamily: 'monospace', maxWidth: '95px',
        }}
      >
        {Object.entries(LABELS).map(([key, label]) => (
          <option key={key} value={key}>{label}</option>
        ))}
      </select>

      {/* Gear button — opens config popover (only for types that have params) */}
      {hasParamsForm && (
        <button
          onClick={() => setShowParams(!showParams)}
          title="Configure transformation"
          style={{
            cursor: 'pointer', flexShrink: 0, width: '22px', height: '20px',
            padding: 0, borderRadius: '3px', border: '1px solid #334155',
            background: showParams ? '#1d4ed8' : hasApplied ? '#14532d' : hasAllParams ? '#78350f' : '#1e293b',
            color: showParams ? '#fff' : hasApplied ? '#86efac' : hasAllParams ? '#fde68a' : '#64748b',
            fontSize: '11px', lineHeight: '18px', textAlign: 'center',
          }}
        >⚙</button>
      )}

      {/* Auto-applying types (to_integer) or summary when popover is closed */}
      {!showParams && currentType !== 'none' && !hasParamsForm && onApply && (
        <button
          onClick={() => onApply(value!)}
          disabled={applying}
          style={{
            cursor: 'pointer', flexShrink: 0, padding: '1px 6px', borderRadius: '3px',
            border: '1px solid #3b82f6', background: '#1d4ed8', color: '#fff',
            fontSize: '10px', fontWeight: 600,
          }}
        >{applying ? '...' : 'Apply'}</button>
      )}

      {/* Compact summary label (shown when popover closed, params configured) */}
      {!showParams && hasApplied && hasParamsForm && (
        <span style={{ fontSize: '8px', color: '#86efac', fontWeight: 600, flexShrink: 0 }}>
          {summary(value)}
        </span>
      )}

      {/* Floating popover with params + Apply */}
      {showParams && hasParamsForm && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, zIndex: 50,
          marginTop: '4px', padding: '10px 12px', minWidth: '200px',
          background: '#1a1f2e', borderRadius: '8px', border: '1px solid #475569',
          boxShadow: '0 6px 20px rgba(0,0,0,0.6)',
        }}>
          <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '8px', fontWeight: 600 }}>
            {LABELS[currentType]}
          </div>
          {requiredParams.map(param => (
            <div key={param} style={{ marginBottom: '6px' }}>
              <label style={{ fontSize: '10px', color: '#94a3b8', display: 'block', marginBottom: '2px' }}>
                {PARAM_LABELS[param] || param}
              </label>
              <input
                value={currentParams[param] || ''}
                onChange={e => handleParamChange(param, e.target.value)}
                placeholder={param}
                autoFocus={requiredParams.indexOf(param) === 0}
                style={{
                  width: '100%', background: '#0f172a', border: '1px solid #334155',
                  borderRadius: '3px', padding: '4px 6px', color: '#f1f5f9',
                  fontSize: '11px', fontFamily: 'monospace', boxSizing: 'border-box',
                }}
              />
            </div>
          ))}

          {/* Preview */}
          {rawValue && hasAllParams && (
            <div style={{
              marginBottom: '8px', padding: '4px 8px', background: '#0f172a', borderRadius: '4px',
              fontSize: '10px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '6px',
            }}>
              <code style={{ color: '#f1f5f9' }}>{rawValue}</code>
              <span>→</span>
              <code style={{ color: applyResult ? '#86efac' : '#64748b' }}>
                {applyResult || '(will compute)'}
              </code>
            </div>
          )}

          {onApply && (
            <button
              onClick={() => { onApply(value!); setShowParams(false); }}
              disabled={applying || !hasAllParams}
              title={!hasAllParams ? 'Fill all required params first' : 'Execute transformation'}
              style={{
                width: '100%', padding: '5px 8px', borderRadius: '4px',
                border: '1px solid #3b82f6',
                background: applying ? '#1e3a5f' : hasAllParams ? '#1d4ed8' : '#1e293b',
                color: hasAllParams ? '#fff' : '#64748b',
                cursor: hasAllParams && !applying ? 'pointer' : 'not-allowed',
                fontSize: '11px', fontWeight: 600,
              }}
            >
              {applying ? 'Applying...' : 'Apply Transformation'}
            </button>
          )}
          {applyError && (
            <div style={{ marginTop: '6px', fontSize: '10px', color: '#fca5a5' }}>{applyError}</div>
          )}
        </div>
      )}
    </div>
  );
}
