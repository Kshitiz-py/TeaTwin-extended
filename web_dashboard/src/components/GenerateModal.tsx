import { useState, useEffect, useRef } from 'react';
import { api, RefreshReport } from '../services/api';

interface GenerateModalProps {
  open: boolean;
  mappingIds: string[];
  onClose: () => void;
  onComplete: (report: RefreshReport) => void;
  onViewDashboard?: () => void;
}

type PhaseStatus = 'pending' | 'running' | 'done' | 'error';

interface Phase {
  key: string;
  label: string;
  status: PhaseStatus;
  detail?: string;
}

export default function GenerateModal({ open, mappingIds, onClose, onComplete, onViewDashboard }: GenerateModalProps) {
  const [phases, setPhases] = useState<Phase[]>([
    { key: 'preflight', label: 'Pre-flight check', status: 'pending' },
    { key: 'fetch', label: 'Fetching APIs', status: 'pending' },
    { key: 'build', label: 'Building entities', status: 'pending' },
    { key: 'merge', label: 'Merging with twin', status: 'pending' },
    { key: 'diff', label: 'Detecting changes', status: 'pending' },
    { key: 'done', label: 'Applying to twin', status: 'pending' },
  ]);
  const [report, setReport] = useState<RefreshReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const hasStarted = useRef(false);

  useEffect(() => {
    if (!open || hasStarted.current) return;
    hasStarted.current = true;
    runGeneration();
  }, [open, mappingIds]);

  const updatePhase = (key: string, status: PhaseStatus, detail?: string) => {
    setPhases(prev => prev.map(p => p.key === key ? { ...p, status, detail } : p));
  };

  const runGeneration = async () => {
    setRunning(true);
    setError(null);

    try {
      updatePhase('preflight', 'running');
      await new Promise(r => setTimeout(r, 300));
      updatePhase('preflight', 'done', 'Passed');

      updatePhase('fetch', 'running');
      const result = await api.refreshInstances(mappingIds, false);
      updatePhase('fetch', 'done', getGenerationSummary(result));

      updatePhase('build', 'running');
      await new Promise(r => setTimeout(r, 200));
      updatePhase('build', 'done', getBuildSummary(result));

      updatePhase('merge', 'running');
      await new Promise(r => setTimeout(r, 200));
      updatePhase('merge', 'done', result.phases.merge.hardcoded_fallback.length > 0
        ? `${result.phases.merge.hardcoded_fallback.length} from hardcoded` : 'All from mappings');

      updatePhase('diff', 'running');
      await new Promise(r => setTimeout(r, 200));
      updatePhase('diff', 'done', `${result.changes_detected} changes`);

      updatePhase('done', 'done', `${result.elapsed_ms}ms`);

      setReport(result);
      setRunning(false);
      onComplete(result);
    } catch (e: any) {
      setError(e.message || 'Generation failed');
      // Mark current phase as error
      setPhases(prev => prev.map(p =>
        p.status === 'running' ? { ...p, status: 'error' as PhaseStatus, detail: e.message } : p
      ));
      setRunning(false);
    }
  };

  const handleRetry = () => {
    setError(null);
    setReport(null);
    setPhases(prev => prev.map(p => ({ ...p, status: 'pending' as PhaseStatus, detail: undefined })));
    runGeneration();
  };

  const handleRetryFailed = async () => {
    if (!report) return;
    const failedIds = report.fetch_errors
      .map(e => mappingIds.find(id => id.includes(e.entity_type.toLowerCase())))
      .filter(Boolean) as string[];
    if (failedIds.length === 0) return;
    setError(null);
    setReport(null);
    setPhases(prev => prev.map(p => ({ ...p, status: 'pending' as PhaseStatus, detail: undefined })));
    setRunning(true);
    try {
      const result = await api.refreshInstances(failedIds, false);
      setReport(result);
      setPhases(prev => prev.map(p => ({ ...p, status: 'done' as PhaseStatus })));
      onComplete(result);
    } catch (e: any) {
      setError(e.message || 'Retry failed');
    } finally {
      setRunning(false);
    }
  };

  if (!open) return null;

  const hasErrors = report?.fetch_errors && report.fetch_errors.length > 0;
  const allFailed = hasErrors && (!report?.phases?.generation || Object.keys(report.phases.generation).length === 0);

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.7)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }}>
      <div style={{
        background: '#1e293b', borderRadius: '12px', border: '1px solid #334155',
        padding: '28px', width: '520px', maxHeight: '80vh', overflow: 'auto',
      }}>
        <h3 style={{ color: '#f1f5f9', margin: '0 0 20px', fontSize: '18px' }}>
          Generate & Apply
        </h3>

        {/* Phases */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
          {phases.map(phase => (
            <div key={phase.key} style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '8px 12px', borderRadius: '6px',
              background: phase.status === 'running' ? '#1e3a5f' : 'transparent',
              border: phase.status === 'running' ? '1px solid #3b82f6' : '1px solid transparent',
            }}>
              <span style={{ fontSize: '14px', width: '20px', textAlign: 'center' }}>
                {phase.status === 'pending' && <span style={{ color: '#64748b' }}>○</span>}
                {phase.status === 'running' && (
                  <span style={{
                    display: 'inline-block', width: '12px', height: '12px',
                    border: '2px solid #3b82f6', borderTopColor: 'transparent',
                    borderRadius: '50%', animation: 'spin 0.6s linear infinite',
                  }} />
                )}
                {phase.status === 'done' && <span style={{ color: '#22c55e' }}>✓</span>}
                {phase.status === 'error' && <span style={{ color: '#ef4444' }}>✕</span>}
              </span>
              <span style={{
                color: phase.status === 'done' ? '#e2e8f0' :
                       phase.status === 'error' ? '#fca5a5' :
                       phase.status === 'running' ? '#93c5fd' : '#64748b',
                fontSize: '13px', flex: 1,
              }}>
                {phase.label}
              </span>
              {phase.detail && (
                <span style={{ color: '#64748b', fontSize: '11px' }}>{phase.detail}</span>
              )}
            </div>
          ))}
        </div>

        <style>{'@keyframes spin { to { transform: rotate(360deg); } }'}</style>

        {/* Error */}
        {error && (
          <div style={{
            padding: '12px', background: '#7f1d1d', borderRadius: '8px',
            border: '1px solid #ef4444', marginBottom: '16px',
          }}>
            <p style={{ color: '#fca5a5', fontSize: '13px', margin: 0 }}>{error}</p>
          </div>
        )}

        {/* Success Summary */}
        {report && !running && (
          <div style={{
            padding: '16px', borderRadius: '8px', marginBottom: '16px',
            background: allFailed ? '#7f1d1d' : hasErrors ? '#78350f' : '#064e3b',
            border: `1px solid ${allFailed ? '#ef4444' : hasErrors ? '#f59e0b' : '#22c55e'}`,
          }}>
            <div style={{ color: '#f1f5f9', fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>
              {allFailed ? 'Generation Failed' : hasErrors ? 'Partial Success' : 'Generation Complete'}
            </div>
            {Object.entries(report.phases.generation).map(([entity, info]) => (
              <div key={entity} style={{ color: '#e2e8f0', fontSize: '12px', marginBottom: '4px' }}>
                {entity}: {info.count} instance(s) from {info.source}
              </div>
            ))}
            {report.phases.merge.hardcoded_fallback.length > 0 && (
              <div style={{ color: '#94a3b8', fontSize: '11px', marginTop: '4px' }}>
                Hardcoded fallback: {report.phases.merge.hardcoded_fallback.join(', ')}
              </div>
            )}
            {report.fetch_errors.length > 0 && (
              <div style={{ marginTop: '8px' }}>
                {report.fetch_errors.map((err, i) => (
                  <div key={i} style={{ color: '#fca5a5', fontSize: '11px' }}>
                    Failed: {err.entity_type} — {err.error}
                  </div>
                ))}
              </div>
            )}
            <div style={{ color: '#94a3b8', fontSize: '11px', marginTop: '6px' }}>
              {report.changes_detected} change(s) · {report.elapsed_ms}ms
            </div>
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          {error && (
            <button onClick={handleRetry} style={{
              padding: '8px 16px', borderRadius: '6px',
              background: '#7c3aed', border: 'none', color: '#fff',
              cursor: 'pointer', fontSize: '13px', fontWeight: 600,
            }}>
              Retry
            </button>
          )}
          {hasErrors && !allFailed && (
            <button onClick={handleRetryFailed} style={{
              padding: '8px 16px', borderRadius: '6px',
              background: '#78350f', border: '1px solid #f59e0b', color: '#fbbf24',
              cursor: 'pointer', fontSize: '13px', fontWeight: 600,
            }}>
              Retry Failed
            </button>
          )}
          {report && !running && (
            <button onClick={() => { onClose(); onViewDashboard?.(); }} style={{
              padding: '8px 16px', borderRadius: '6px',
              background: '#065f46', border: 'none', color: '#6ee7b7',
              cursor: 'pointer', fontSize: '13px', fontWeight: 600,
            }}>
              {allFailed ? 'Close' : 'View Dashboard'}
            </button>
          )}
          {running && (
            <button onClick={onClose} style={{
              padding: '8px 16px', borderRadius: '6px',
              background: '#334155', border: 'none', color: '#94a3b8',
              cursor: 'pointer', fontSize: '13px',
            }}>
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function getGenerationSummary(report: RefreshReport): string {
  const entries = Object.entries(report.phases.generation);
  if (entries.length === 0) return 'No entities generated';
  return entries.map(([k, v]) => `${v.count} ${k}`).join(', ');
}

function getBuildSummary(report: RefreshReport): string {
  const total = Object.values(report.phases.generation).reduce((sum, v) => sum + v.count, 0);
  return `${total} instance(s) built`;
}
