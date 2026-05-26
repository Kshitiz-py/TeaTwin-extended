import { useState, useEffect, useCallback } from 'react';
import AgentConnect from './AgentConnect';
import ConnectSources from './ConnectSources';
import MappingWizard from './MappingWizard';
import GuidedMapping from './GuidedMapping';
import ValidationDashboard from './ValidationDashboard';
import { SourceData } from './SourceCard';
import {
  agentApi, AgentStatus, QueuedMapping, GeneratedDiff, CodeGenerationReport,
  GenerationStatus, ApplyResult,
} from '../services/agentApi';

const STEPS = [
  { key: 'llm'       as const, label: 'Connect LLM',        icon: '🤖' },
  { key: 'connect'   as const, label: 'Connect Sources',    icon: '🔗' },
  { key: 'explorer'  as const, label: 'API Explorer',       icon: '🔍' },
  { key: 'mapping'   as const, label: 'Guided Mapping',     icon: '🧩' },
  { key: 'validate'  as const, label: 'Validate & Run',     icon: '✅' },
  { key: 'queue'     as const, label: 'Review Queue',       icon: '📋' },
  { key: 'generate'  as const, label: 'Generate & Apply',   icon: '🚀' },
];

interface SetupWizardProps {
  onLaunch: () => void;
  onDisconnected?: () => void;
}

export default function SetupWizard({ onLaunch, onDisconnected }: SetupWizardProps) {
  const [activeStep, setActiveStep] = useState(0);
  const [sources, setSources] = useState<SourceData[]>([]);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [llmConnected, setLlmConnected] = useState(false);

  // ── Queue state ────────────────────────────────────────────
  const [queue, setQueue] = useState<QueuedMapping[]>([]);
  const [queueLoading, setQueueLoading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  // ── Generation state ───────────────────────────────────────
  const [genStatus, setGenStatus] = useState<GenerationStatus | null>(null);
  const [genDiff, setGenDiff] = useState<GeneratedDiff | null>(null);
  const [genReport, setGenReport] = useState<CodeGenerationReport | null>(null);
  const [genLoading, setGenLoading] = useState(false);
  const [genError, setGenError] = useState('');
  const [applyLoading, setApplyLoading] = useState(false);
  const [applyResult, setApplyResult] = useState<ApplyResult | null>(null);

  // Fetch agent status on mount and periodically
  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const s = await agentApi.getAgentStatus();
        if (!cancelled) {
          setAgentStatus(s);
          setLlmConnected(s.connected);
        }
      } catch {
        if (!cancelled) setAgentStatus(null);
      }
    };
    check();
    const interval = setInterval(check, 10000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  const handleLlmConnected = () => {
    setLlmConnected(true);
    setActiveStep(1);
  };

  const handleLlmDisconnected = () => {
    setLlmConnected(false);
    setAgentStatus({ connected: false });
    onDisconnected?.();
  };

  const handleSourcesComplete = (connectedSources: SourceData[]) => {
    setSources(connectedSources);
    setActiveStep(2); // → API Explorer
  };

  const handleMappingComplete = () => {
    setActiveStep(4); // → Validate & Run
  };

  // ── Step 4 callbacks ────────────────────────────────────────

  const loadQueue = useCallback(async () => {
    setQueueLoading(true);
    try {
      const resp = await agentApi.getMappingQueue();
      setQueue(resp.mappings);
    } catch (e) {
      console.error('Failed to load mapping queue:', e);
    } finally {
      setQueueLoading(false);
    }
  }, []);

  const handleRemoveFromQueue = async (mappingId: string) => {
    try {
      await agentApi.removeFromQueue(mappingId);
      setQueue(prev => prev.filter(m => m.mapping_id !== mappingId));
    } catch (e) {
      console.error('Failed to remove from queue:', e);
    }
  };

  const handleStartEditing = (m: QueuedMapping) => {
    setEditingId(m.mapping_id);
    setEditText(JSON.stringify({ data_point: m.data_point, cmsd_entity: m.cmsd_entity }, null, 2));
  };

  const handleSaveEdit = async (mappingId: string) => {
    try {
      const parsed = JSON.parse(editText);
      await agentApi.editQueuedMapping(mappingId, parsed);
      setQueue(prev => prev.map(m =>
        m.mapping_id === mappingId ? { ...m, ...parsed } : m
      ));
      setEditingId(null);
    } catch (e) {
      console.error('Failed to save edit:', e);
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
  };

  // ── Step 5 callbacks ────────────────────────────────────────

  const handleTriggerGeneration = async () => {
    setGenLoading(true);
    setGenError('');
    setGenDiff(null);
    setGenReport(null);
    setApplyResult(null);
    try {
      const result = await agentApi.triggerCodeGeneration();
      setGenReport(result.report);
      setGenDiff(result.diff);
      setGenStatus({
        has_generated_code: result.success,
        has_report: true,
        queue_size: result.report.batch_size,
        generation_branch: result.diff.branch,
        files_changed: result.diff.files_changed,
      });
    } catch (e: any) {
      setGenError(e.message || 'Code generation failed');
    } finally {
      setGenLoading(false);
    }
  };

  const handleApplyGeneration = async () => {
    setApplyLoading(true);
    try {
      const result = await agentApi.applyCodeGeneration();
      setApplyResult(result);
      if (result.success) {
        // Move to launch
        setTimeout(() => onLaunch(), 1500);
      }
    } catch (e: any) {
      setGenError(e.message || 'Apply failed');
    } finally {
      setApplyLoading(false);
    }
  };

  const handleRollbackGeneration = async () => {
    setGenLoading(true);
    try {
      await agentApi.rollbackCodeGeneration();
      setGenDiff(null);
      setGenReport(null);
      setApplyResult(null);
      setGenError('Rolled back the last generation.');
    } catch (e: any) {
      setGenError(e.message || 'Rollback failed');
    } finally {
      setGenLoading(false);
    }
  };

  const handleViewDiff = async () => {
    try {
      const diff = await agentApi.getGenerationDiff();
      setGenDiff(diff);
    } catch (e: any) {
      setGenError(e.message || 'Failed to load diff');
    }
  };

  const step = STEPS[activeStep];

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a' }}>
      {/* Header */}
      <header style={{
        background: '#1e293b', padding: '12px 24px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: '1px solid #334155',
      }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#f1f5f9', margin: 0 }}>
            CMSD Digital Twin — Setup Wizard
          </h1>
          <p style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
            AI-guided API to CMSD mapping — connect LLM, map, validate, generate
          </p>
        </div>
        {agentStatus?.connected ? (
          <span style={{
            padding: '4px 12px', borderRadius: '12px', fontSize: '12px',
            background: '#064e3b', color: '#6ee7b7',
          }}>
            ● {agentStatus.provider_type ?? 'LLM'} — {agentStatus.chat_model}
          </span>
        ) : (
          <span style={{
            padding: '4px 12px', borderRadius: '12px', fontSize: '12px',
            background: '#7f1d1d', color: '#fca5a5',
          }}>
            ○ LLM not connected
          </span>
        )}
      </header>

      {/* Stepper */}
      <div style={{
        display: 'flex', justifyContent: 'center', padding: '20px 24px',
        background: '#0f172a', borderBottom: '1px solid #334155',
      }}>
        <div style={{ display: 'flex', gap: '0', alignItems: 'center' }}>
          {STEPS.map((s, i) => {
            const isActive = i === activeStep;
            const isCompleted = i < activeStep;
            const canClick = isCompleted || (i <= activeStep + 1 && i !== 0);
            return (
              <div key={s.key} style={{ display: 'flex', alignItems: 'center' }}>
                <button
                  onClick={() => canClick && setActiveStep(i)}
                  disabled={!canClick}
                  style={{
                    padding: '8px 16px', borderRadius: '8px', border: '2px solid',
                    borderColor: isActive ? '#818cf8' : isCompleted ? '#34d399' : '#334155',
                    background: isActive ? '#1e293b' : isCompleted ? '#064e3b' : '#0f172a',
                    color: isActive ? '#e2e8f0' : isCompleted ? '#6ee7b7' : '#64748b',
                    cursor: canClick ? 'pointer' : 'default',
                    fontSize: '12px', fontWeight: 600,
                    display: 'flex', alignItems: 'center', gap: '6px',
                    opacity: canClick ? 1 : 0.5,
                    transition: 'all 0.2s',
                    whiteSpace: 'nowrap',
                  }}
                >
                  <span>{s.icon}</span>
                  <span>{s.label}</span>
                </button>
                {i < STEPS.length - 1 && (
                  <div style={{
                    width: '28px', height: '2px',
                    background: i < activeStep ? '#34d399' : '#334155',
                    margin: '0 4px',
                  }} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Step Content */}
      <div style={{ padding: '24px' }}>
        {step.key === 'llm' && (
          <AgentConnect onConnected={handleLlmConnected} onDisconnected={handleLlmDisconnected} />
        )}
        {step.key === 'connect' && (
          <ConnectSources
            onSourcesComplete={handleSourcesComplete}
            agentConnected={llmConnected}
          />
        )}
        {step.key === 'explorer' && (
          <MappingWizard />
        )}
        {step.key === 'mapping' && (
          <GuidedMapping
            sources={sources}
            onComplete={handleMappingComplete}
          />
        )}
        {step.key === 'validate' && (
          <ValidationDashboard
            sources={sources}
            onLaunch={() => setActiveStep(5)}
          />
        )}

        {/* ── Step 4: Review Queue ───────────────────── */}
        {step.key === 'queue' && (
          <div style={{ maxWidth: '900px', margin: '0 auto' }}>
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              marginBottom: '20px',
            }}>
              <div>
                <h2 style={{ color: '#f1f5f9', margin: '0 0 4px', fontSize: '20px' }}>
                  📋 Confirmed Mapping Queue
                </h2>
                <p style={{ color: '#94a3b8', margin: 0, fontSize: '13px' }}>
                  Review, edit, or remove confirmed mappings before generating the twin code.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={loadQueue}
                  disabled={queueLoading}
                  style={{
                    padding: '8px 16px', borderRadius: '6px',
                    background: '#1e293b', border: '1px solid #475569',
                    color: '#cbd5e1', cursor: 'pointer', fontSize: '13px',
                  }}
                >
                  {queueLoading ? '⏳ Loading...' : '🔄 Refresh'}
                </button>
                <button
                  onClick={() => setActiveStep(6)}
                  disabled={queue.length === 0}
                  style={{
                    padding: '8px 20px', borderRadius: '6px',
                    background: queue.length > 0 ? '#7c3aed' : '#334155',
                    border: 'none', color: '#fff', cursor: queue.length > 0 ? 'pointer' : 'default',
                    fontWeight: 600, fontSize: '13px',
                  }}
                >
                  Next: Generate Code →
                </button>
              </div>
            </div>

            {queue.length === 0 ? (
              <div style={{
                padding: '48px', textAlign: 'center', background: '#1e293b',
                borderRadius: '12px', border: '1px dashed #475569',
              }}>
                <p style={{ color: '#94a3b8', fontSize: '14px', margin: 0 }}>
                  {queueLoading
                    ? 'Loading queue...'
                    : 'No confirmed mappings yet. Go back to the Guided Mapping step and confirm some mappings.'}
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {queue.map((m) => (
                  <div key={m.mapping_id} style={{
                    padding: '14px 16px', background: '#1e293b',
                    borderRadius: '8px', border: '1px solid #334155',
                    display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
                    gap: '16px',
                  }}>
                    {editingId === m.mapping_id ? (
                      <div style={{ flex: 1 }}>
                        <textarea
                          value={editText}
                          onChange={e => setEditText(e.target.value)}
                          rows={4}
                          style={{
                            width: '100%', padding: '8px', borderRadius: '6px',
                            background: '#0f172a', border: '1px solid #475569',
                            color: '#e2e8f0', fontFamily: 'monospace', fontSize: '12px',
                            resize: 'vertical',
                          }}
                        />
                        <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                          <button
                            onClick={() => handleSaveEdit(m.mapping_id)}
                            style={{
                              padding: '4px 14px', borderRadius: '4px',
                              background: '#065f46', border: 'none', color: '#6ee7b7',
                              cursor: 'pointer', fontSize: '12px', fontWeight: 600,
                            }}
                          >
                            Save
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            style={{
                              padding: '4px 14px', borderRadius: '4px',
                              background: '#334155', border: 'none', color: '#94a3b8',
                              cursor: 'pointer', fontSize: '12px',
                            }}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', gap: '10px', alignItems: 'baseline', marginBottom: '4px' }}>
                            <span style={{ color: '#f1f5f9', fontWeight: 600, fontSize: '14px' }}>
                              {m.data_point}
                            </span>
                            <span style={{ color: '#64748b', fontSize: '11px' }}>→</span>
                            <span style={{ color: '#a78bfa', fontWeight: 600, fontSize: '14px' }}>
                              {m.cmsd_entity}
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: '16px', fontSize: '11px', color: '#64748b' }}>
                            <span>ID: {m.mapping_id}</span>
                            <span>
                              Confirmed: {new Date(m.confirmed_at).toLocaleString()}
                            </span>
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                          <button
                            onClick={() => handleStartEditing(m)}
                            style={{
                              padding: '4px 12px', borderRadius: '4px',
                              background: '#1e3a5f', border: 'none', color: '#93c5fd',
                              cursor: 'pointer', fontSize: '12px',
                            }}
                          >
                            ✏️ Edit
                          </button>
                          <button
                            onClick={() => handleRemoveFromQueue(m.mapping_id)}
                            style={{
                              padding: '4px 12px', borderRadius: '4px',
                              background: '#7f1d1d', border: 'none', color: '#fca5a5',
                              cursor: 'pointer', fontSize: '12px',
                            }}
                          >
                            🗑 Remove
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Step 5: Generate & Apply ──────────────── */}
        {step.key === 'generate' && (
          <div style={{ maxWidth: '900px', margin: '0 auto' }}>
            <div style={{ marginBottom: '20px' }}>
              <h2 style={{ color: '#f1f5f9', margin: '0 0 4px', fontSize: '20px' }}>
                🚀 Code Generation & Review
              </h2>
              <p style={{ color: '#94a3b8', margin: 0, fontSize: '13px' }}>
                Run the 3-agent pipeline (Writer → Reviewer → Tester) on all queued mappings and review the generated diffs.
              </p>
            </div>

            {/* Action buttons */}
            <div style={{
              display: 'flex', gap: '12px', marginBottom: '20px',
              padding: '16px', background: '#1e293b', borderRadius: '8px',
              border: '1px solid #334155', flexWrap: 'wrap', alignItems: 'center',
            }}>
              <button
                onClick={handleTriggerGeneration}
                disabled={genLoading}
                style={{
                  padding: '10px 24px', borderRadius: '8px',
                  background: genLoading ? '#334155' : '#7c3aed',
                  border: 'none', color: genLoading ? '#64748b' : '#fff',
                  cursor: genLoading ? 'default' : 'pointer',
                  fontWeight: 600, fontSize: '14px',
                  display: 'flex', alignItems: 'center', gap: '8px',
                }}
              >
                {genLoading ? '⏳' : '⚡'} {genLoading ? 'Generating...' : 'Generate Twin Code'}
              </button>
              <button
                onClick={handleViewDiff}
                style={{
                  padding: '10px 20px', borderRadius: '8px',
                  background: '#1e293b', border: '1px solid #475569',
                  color: '#cbd5e1', cursor: 'pointer', fontWeight: 600, fontSize: '14px',
                }}
              >
                📄 View Diff
              </button>
              {genDiff && (
                <>
                  <button
                    onClick={handleApplyGeneration}
                    disabled={applyLoading}
                    style={{
                      padding: '10px 24px', borderRadius: '8px',
                      background: applyLoading ? '#334155' : '#065f46',
                      border: 'none', color: applyLoading ? '#64748b' : '#6ee7b7',
                      cursor: applyLoading ? 'default' : 'pointer',
                      fontWeight: 600, fontSize: '14px',
                    }}
                  >
                    {applyLoading ? '⏳' : '✅'} Apply & Merge
                  </button>
                  <button
                    onClick={handleRollbackGeneration}
                    style={{
                      padding: '10px 20px', borderRadius: '8px',
                      background: '#7f1d1d', border: 'none', color: '#fca5a5',
                      cursor: 'pointer', fontWeight: 600, fontSize: '14px',
                    }}
                  >
                    ↩ Rollback
                  </button>
                </>
              )}
            </div>

            {/* Error */}
            {genError && (
              <div style={{
                padding: '12px 16px', background: '#7f1d1d', borderRadius: '8px',
                border: '1px solid #ef4444', color: '#fca5a5', fontSize: '13px',
                marginBottom: '16px',
              }}>
                {genError}
              </div>
            )}

            {/* Apply result */}
            {applyResult && (
              <div style={{
                padding: '16px', borderRadius: '8px', marginBottom: '16px',
                background: applyResult.success ? '#064e3b' : '#7f1d1d',
                border: `1px solid ${applyResult.success ? '#34d399' : '#ef4444'}`,
                color: applyResult.success ? '#6ee7b7' : '#fca5a5',
                fontSize: '14px',
              }}>
                <strong>{applyResult.success ? '✅ Applied!' : '❌ Apply Failed'}</strong>
                <p style={{ margin: '8px 0 0' }}>{applyResult.message}</p>
                {applyResult.files_changed.length > 0 && (
                  <p style={{ margin: '4px 0 0', fontSize: '12px', opacity: 0.8 }}>
                    Files: {applyResult.files_changed.join(', ')}
                  </p>
                )}
              </div>
            )}

            {/* Report summary */}
            {genReport && (
              <div style={{
                padding: '16px', background: '#1e293b', borderRadius: '8px',
                border: '1px solid #334155', marginBottom: '16px',
              }}>
                <h3 style={{ color: '#f1f5f9', margin: '0 0 10px', fontSize: '15px' }}>
                  📊 Generation Report
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '13px' }}>
                  <div style={{ color: '#94a3b8' }}>Batch Size:</div>
                  <div style={{ color: '#e2e8f0' }}>{genReport.batch_size}</div>
                  <div style={{ color: '#94a3b8' }}>Files Generated:</div>
                  <div style={{ color: '#e2e8f0' }}>{genReport.files_generated.length}</div>
                  <div style={{ color: '#94a3b8' }}>Elapsed:</div>
                  <div style={{ color: '#e2e8f0' }}>{genReport.elapsed_seconds}s</div>
                  <div style={{ color: '#94a3b8' }}>Git Committed:</div>
                  <div style={{ color: genReport.git.committed ? '#6ee7b7' : '#fca5a5' }}>
                    {genReport.git.committed ? 'Yes' : 'No'}
                  </div>
                </div>
                {genReport.files_generated.length > 0 && (
                  <div style={{ marginTop: '10px' }}>
                    <div style={{ color: '#94a3b8', fontSize: '12px', marginBottom: '4px' }}>Files:</div>
                    {genReport.files_generated.map(f => (
                      <div key={f} style={{ color: '#a78bfa', fontSize: '12px', fontFamily: 'monospace' }}>
                        {f}
                      </div>
                    ))}
                  </div>
                )}
                {/* Per-mapping results */}
                <div style={{ marginTop: '12px' }}>
                  <div style={{ color: '#94a3b8', fontSize: '12px', marginBottom: '4px' }}>
                    Mapping Results:
                  </div>
                  {genReport.reports.map(r => (
                    <div key={r.mapping_id} style={{
                      padding: '6px 10px', marginBottom: '4px', borderRadius: '4px',
                      background: r.success ? '#064e3b' : '#7f1d1d',
                      display: 'flex', justifyContent: 'space-between',
                      fontSize: '12px',
                    }}>
                      <span style={{ color: '#e2e8f0' }}>
                        {r.data_point} → {r.cmsd_entity}
                      </span>
                      <span style={{ color: r.success ? '#6ee7b7' : '#fca5a5' }}>
                        {r.success ? '✅ Pass' : `❌ ${r.error || 'Failed'}`}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Unified diff */}
            {genDiff && (
              <div style={{
                padding: '16px', background: '#1e293b', borderRadius: '8px',
                border: '1px solid #334155',
              }}>
                <h3 style={{ color: '#f1f5f9', margin: '0 0 10px', fontSize: '15px' }}>
                  📄 Unified Diff <span style={{ color: '#64748b', fontSize: '12px' }}>
                    ({genDiff.files_changed.length} files on branch {genDiff.branch})
                  </span>
                </h3>
                <pre style={{
                  padding: '16px', background: '#0f172a', borderRadius: '6px',
                  border: '1px solid #334155', overflow: 'auto', maxHeight: '400px',
                  color: '#e2e8f0', fontSize: '12px', fontFamily: 'monospace',
                  lineHeight: '1.6', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                }}>
                  {genDiff.unified_diff || '(empty diff)'}
                </pre>
              </div>
            )}

            {!genDiff && !genReport && !genLoading && (
              <div style={{
                padding: '48px', textAlign: 'center', background: '#1e293b',
                borderRadius: '12px', border: '1px dashed #475569',
              }}>
                <p style={{ color: '#94a3b8', fontSize: '14px', margin: 0 }}>
                  Click <strong>"Generate Twin Code"</strong> to run the 3-agent pipeline on all queued mappings.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}