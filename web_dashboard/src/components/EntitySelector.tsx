import { useEffect, useCallback } from 'react';

interface Props {
  entities: string[];
  currentEntity: string;
  onChange: (entity: string) => void;
  mappedCount?: number;
}

export default function EntitySelector({ entities, currentEntity, onChange, mappedCount }: Props) {
  const currentIndex = entities.indexOf(currentEntity);
  const prevEntity = currentIndex > 0 ? entities[currentIndex - 1] : entities[entities.length - 1];
  const nextEntity = currentIndex < entities.length - 1 ? entities[currentIndex + 1] : entities[0];

  const navigateTo = useCallback((direction: 'prev' | 'next') => {
    onChange(direction === 'prev' ? prevEntity : nextEntity);
  }, [prevEntity, nextEntity, onChange]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Skip when focus is in text inputs, textareas, or selects
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (e.ctrlKey && e.key === 'ArrowLeft') {
        e.preventDefault();
        navigateTo('prev');
      } else if (e.ctrlKey && e.key === 'ArrowRight') {
        e.preventDefault();
        navigateTo('next');
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [navigateTo]);

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '6px',
      marginBottom: '16px',
    }}>
      <button
        onClick={() => navigateTo('prev')}
        title={`Previous entity (Ctrl+Left)\n${prevEntity}`}
        style={{
          padding: '6px 10px', borderRadius: '6px',
          border: '1px solid #475569', background: '#1e293b',
          color: '#94a3b8', cursor: 'pointer', fontSize: '14px',
          fontWeight: 600, lineHeight: 1,
        }}
      >
        &#9664;
      </button>

      <div style={{ flex: 1, minWidth: '200px' }}>
        <label style={{
          fontSize: '10px', color: '#64748b', display: 'block',
          marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px',
        }}>
          CMSD Entity
        </label>
        <select
          value={currentEntity}
          onChange={e => onChange(e.target.value)}
          style={{
            width: '100%', background: '#0f172a', border: '1px solid #475569',
            borderRadius: '6px', padding: '8px 10px', color: '#f1f5f9',
            fontSize: '14px', fontWeight: 600, fontFamily: 'monospace',
          }}
        >
          {entities.map(entity => (
            <option key={entity} value={entity}>{entity}</option>
          ))}
        </select>
      </div>

      <button
        onClick={() => navigateTo('next')}
        title={`Next entity (Ctrl+Right)\n${nextEntity}`}
        style={{
          padding: '6px 10px', borderRadius: '6px',
          border: '1px solid #475569', background: '#1e293b',
          color: '#94a3b8', cursor: 'pointer', fontSize: '14px',
          fontWeight: 600, lineHeight: 1,
        }}
      >
        &#9654;
      </button>

      {mappedCount !== undefined && (
        <span style={{
          fontSize: '11px', color: '#64748b', whiteSpace: 'nowrap',
          marginLeft: '4px',
        }}>
          ({mappedCount} mapped)
        </span>
      )}
    </div>
  );
}
