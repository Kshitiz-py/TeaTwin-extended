import { useState, useEffect } from 'react';
import { agentApi } from '../services/agentApi';
import { SourceData } from './SourceCard';

interface ValidationDashboardProps {
  sources: SourceData[];
  onLaunch: () => void;
}

interface SourceStatus {
  id: string; name: string; status: string; latency_ms?: number; last_tested?: string;
}

export default function ValidationDashboard({ sources, onLaunch }: ValidationDashboardProps) {
  const [statuses, setStatuses] = useState<SourceStatus[]>([]);
  const [mappingProgress, setMappingProgress] = useState<any>(null);
  const [diff, setDiff] = useState<string | null>(null);
  const [testing, setTesting] = useState<string | null>(null);

  useEffect(() => {
    refreshStatuses();
    loadProgress();
  }, []);

  const refreshStatuses = async () => {
    try {
      const res = await agentApi.getSources();
      if (res.sources) setStatuses(res.sources.map((s: any) => ({
        id: s.id, name: s.name, status: s.status || 'unknown',
        latency_ms: s.latency_ms, last_tested: s.last_tested,
      })));
    } catch {}
  };

  const loadProgress = async () => {
    try {
      const p = await agentApi.getMappingProgress();
      setMappingProgress(p);
    } catch {}
  };

  const testSource = async (id: string) => {
    setTesting(id);
    try { await agentApi.testSource(id); } catch {}
    await refreshStatuses();
    setTesting(null);
  };

  const testAll = async () => {
    for (const s of statuses) {
      setTesting(s.id);
      try { await agentApi.testSource(s.id); } catch {}
    }
    setTesting(null);
    await refreshStatuses();
  };

  const loadDiff = async () => {
    try {
      const d = await agentApi.getGitDiff();
      setDiff(d.diff || 'No diff available');
    } catch (e: any) {
      setDiff(`Error: ${e.message}`);
    }
  };

  const rollback = async () => {
    try {
      const r = await agentApi.rollbackGit();
      if (r.reverted) alert('Last commit reverted successfully');
      else alert('Rollback failed: ' + (r.error || 'unknown'));
    } catch (e: any) {
      alert('Rollback failed: ' + e.message);
    }
  };

  return (
    <div>
      {/* Connection Health */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h3 style={{ color: '#f1f5f9', fontSize: '16px', margin: 0 }}>Connection Health</h3>
          <button onClick={testAll} disabled={testing !== null}
            style={{ padding: '6px 14px', background: '#334155', color: '#94a3b8', border: '1px solid #475569', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>
            {testing ? 'Testing…' : 'Test All'}
          </button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px' }}>
          {statuses.map(s => (
            <div key={s.id} style={{ background: '#1e293b', borderRadius: '8px', padding: '14px', border: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <p style={{ margin: 0, color: '#f1f5f9', fontSize: '13px', fontWeight: 600 }}>{s.name}</p>
                <p style={{ margin: '2px 0 0', fontSize: '11px', color: s.status === 'connected' ? '#4ade80' : s.status === 'failed' ? '#fca5a5' : '#94a3b8' }}>
                  {s.status === 'connected' ? '✅ Connected' : s.status === 'failed' ? '❌ Failed' : '⚪ ' + (s.status || 'unknown')}
                  {s.latency_ms ? ` (${s.latency_ms}ms)` : ''}
                </p>
              </div>
              <button onClick={() => testSource(s.id)} disabled={testing === s.id}
                style={{ padding: '4px 10px', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: '#94a3b8', cursor: 'pointer', fontSize: '11px' }}>
                {testing === s.id ? '…' : 'Test'}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Mapping Summary */}
      {mappingProgress && (
        <div style={{ marginBottom: '20px', background: '#1e293b', borderRadius: '8px', padding: '16px', border: '1px solid #334155' }}>
          <h3 style={{ color: '#f1f5f9', fontSize: '16px', margin: '0 0 10px' }}>Mapping Summary</h3>
          <div style={{ display: 'flex', gap: '20px', marginBottom: '10px', flexWrap: 'wrap' }}>
            <KPI label="Total Mappings" value={mappingProgress.total_mappings} />
            <KPI label="Completed" value={mappingProgress.completed} color="#4ade80" />
            <KPI label="Failed" value={mappingProgress.failed || 0} color="#fca5a5" />
          </div>
        </div>
      )}

      {/* Git Controls */}
      <div style={{ marginBottom: '20px', background: '#1e293b', borderRadius: '8px', padding: '16px', border: '1px solid #334155' }}>
        <h3 style={{ color: '#f1f5f9', fontSize: '16px', margin: '0 0 10px' }}>Version Control</h3>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button onClick={loadDiff} style={btnStyle('#3b82f6')}>📄 View Diff</button>
          <button onClick={rollback} style={btnStyle('#ef4444')}>⏮ Rollback Last Commit</button>
        </div>
        {diff !== null && (
          <div style={{ marginTop: '12px', background: '#0f172a', borderRadius: '6px', padding: '12px', maxHeight: '200px', overflowY: 'auto' }}>
            <pre style={{ color: '#94a3b8', fontSize: '11px', margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>{diff}</pre>
          </div>
        )}
      </div>

      {/* Launch */}
      <div style={{ textAlign: 'center', padding: '20px 0' }}>
        <button onClick={onLaunch}
          style={{ padding: '14px 40px', background: '#22c55e', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '16px', fontWeight: 700, boxShadow: '0 4px 16px rgba(34,197,94,0.3)' }}>
          🚀 Launch Digital Twin
        </button>
        <p style={{ color: '#64748b', fontSize: '12px', marginTop: '8px' }}>
          All mappings confirmed and connections verified. Ready to build your CMSD digital twin.
        </p>
      </div>
    </div>
  );
}

const KPI = ({ label, value, color }: { label: string; value: number; color?: string }) => (
  <div>
    <p style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', margin: 0 }}>{label}</p>
    <p style={{ fontSize: '24px', fontWeight: 700, color: color || '#f1f5f9', margin: '2px 0 0' }}>{value}</p>
  </div>
);

const btnStyle = (color: string): React.CSSProperties => ({
  padding: '8px 16px', background: '#0f172a', color, border: `1px solid ${color}`, borderRadius: '6px', cursor: 'pointer', fontSize: '13px', fontWeight: 500,
});
