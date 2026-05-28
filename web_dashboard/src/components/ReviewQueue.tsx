import { useState, useEffect, useCallback } from 'react';
import { agentApi, MappingSummary } from '../services/agentApi';
import GenerateModal from './GenerateModal';
import { api, RefreshReport, PreflightResult } from '../services/api';

interface ReviewQueueProps {
  embedded?: boolean;
  onGenerate?: (ids: string[]) => void;
  onEdit?: (mappingId: string) => void | Promise<void>;
  onNavigateToExplorer?: () => void;
  onViewDashboard?: () => void;
}

export default function ReviewQueue({ embedded = false, onGenerate, onEdit, onNavigateToExplorer, onViewDashboard }: ReviewQueueProps) {
  const [mappings, setMappings] = useState<MappingSummary[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [generateIds, setGenerateIds] = useState<string[]>([]);

  // Pre-flight state
  const [preflightLoading, setPreflightLoading] = useState(false);
  const [preflightResult, setPreflightResult] = useState<PreflightResult | null>(null);
  const [showDepsPrompt, setShowDepsPrompt] = useState(false);
  const [depsPromptInfo, setDepsPromptInfo] = useState<{
    missing: Array<{ for_mapping: string; for_entity: string; needs: string; needs_entity: string; is_relation?: boolean; relation_path?: string }>;
    autoSelectIds: string[];
  } | null>(null);

  const loadMappings = useCallback(async () => {
    setLoading(true);
    try {
      const data = await agentApi.listMappings();
      setMappings(data.mappings);
    } catch (e) {
      console.error('Failed to load mappings:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMappings();
  }, [loadMappings]);

  const handleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedIds.size === mappings.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(mappings.map(m => m.id)));
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await agentApi.deleteMapping(id);
      setMappings(prev => prev.filter(m => m.id !== id));
      setSelectedIds(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    } catch (e) {
      console.error('Failed to delete mapping:', e);
    }
  };

  const handleEdit = (mapping: MappingSummary) => {
    if (onEdit) {
      onEdit(mapping.id);
    }
  };

  const handleGenerate = async () => {
    if (selectedIds.size === 0) return;
    const ids = Array.from(selectedIds);

    // Run pre-flight before opening GenerateModal (hard block)
    setPreflightLoading(true);
    try {
      const result = await api.validatePreflight(ids);
      setPreflightResult(result);

      if (!result.checks.dependencies.passed || !result.checks.relations?.passed) {
        // Show dependency auto-select prompt (includes relation missing targets)
        const autoSelectIds = result.checks.dependencies?.auto_selected || [];
        const missingDeps = result.checks.dependencies?.missing || [];
        const missingRels = result.checks.relations?.missing_targets || [];
        // Convert relation issues to match dependency prompt format
        const allMissing = [
          ...missingDeps,
          ...missingRels.map(r => ({
            for_mapping: r.for_mapping,
            for_entity: r.for_entity,
            needs: r.target_mapping_id,
            needs_entity: r.target_entity,
            is_relation: true,
            relation_path: r.relation_path,
          })),
        ];
        const allAutoSelect = [...new Set([
          ...autoSelectIds,
          ...missingDeps.map((m: any) => m.needs),
          ...missingRels.map((r: any) => r.target_mapping_id).filter(Boolean),
        ])];
        setDepsPromptInfo({
          missing: allMissing as any,
          autoSelectIds: allAutoSelect as any,
        });
        setShowDepsPrompt(true);
        setPreflightLoading(false);
        return;
      }

      if (!result.passed) {
        // Build a specific message about what failed
        const failures: string[] = [];
        if (!result.checks.field_coverage.passed) {
          const count = result.checks.field_coverage.flagged?.length || 0;
          failures.push(`${count} field(s) flagged for review`);
        }
        if (!result.checks.api_reachability.passed) {
          const count = result.checks.api_reachability.unreachable?.length || 0;
          failures.push(`${count} API source(s) unreachable`);
        }
        setPreflightLoading(false);
        alert(`Cannot generate:\n${failures.join('\n')}\n\nEdit the mapping(s) to resolve these issues.`);
        return;
      }

      setGenerateIds(ids);
      setGenerateOpen(true);
      onGenerate?.(ids);
    } catch (e: any) {
      console.error('Pre-flight failed:', e);
    } finally {
      setPreflightLoading(false);
    }
  };

  const handleAcceptAutoSelect = () => {
    if (!depsPromptInfo) return;
    const newIds = depsPromptInfo.autoSelectIds;
    setSelectedIds(prev => new Set([...prev, ...newIds]));
    setShowDepsPrompt(false);
    setDepsPromptInfo(null);

    // Re-run with expanded selection
    const expanded = [...new Set([...Array.from(selectedIds), ...newIds])];
    setGenerateIds(expanded);
    setGenerateOpen(true);
  };

  const handleDeclineAutoSelect = () => {
    setShowDepsPrompt(false);
    setDepsPromptInfo(null);
  };

  const handleCreateNew = () => {
    if (onNavigateToExplorer) {
      onNavigateToExplorer();
    }
  };

  const formatDate = (iso: string) => {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '20px',
      }}>
        <div>
          <h2 style={{ color: '#f1f5f9', margin: '0 0 4px', fontSize: '20px' }}>
            Mapping Registry
          </h2>
          <p style={{ color: '#94a3b8', margin: 0, fontSize: '13px' }}>
            Review, edit, and select confirmed mappings for instance generation.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={loadMappings}
            disabled={loading}
            style={{
              padding: '8px 16px', borderRadius: '6px',
              background: '#1e293b', border: '1px solid #475569',
              color: '#cbd5e1', cursor: 'pointer', fontSize: '13px',
            }}
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
          <button
            onClick={handleCreateNew}
            style={{
              padding: '8px 16px', borderRadius: '6px',
              background: '#7c3aed', border: 'none',
              color: '#fff', cursor: 'pointer', fontSize: '13px', fontWeight: 600,
            }}
          >
            + Create New
          </button>
        </div>
      </div>

      {/* Empty state */}
      {!loading && mappings.length === 0 ? (
        <div style={{
          padding: '48px', textAlign: 'center', background: '#1e293b',
          borderRadius: '12px', border: '1px dashed #475569',
        }}>
          <p style={{ color: '#94a3b8', fontSize: '14px', margin: 0 }}>
            No confirmed mappings yet. Use the API Explorer to create and confirm mappings.
          </p>
        </div>
      ) : (
        <>
          {/* Table */}
          <div style={{
            background: '#1e293b', borderRadius: '10px', border: '1px solid #334155',
            overflow: 'hidden',
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #334155' }}>
                  <th style={{ padding: '10px 14px', width: '40px' }}>
                    <input
                      type="checkbox"
                      checked={selectedIds.size === mappings.length && mappings.length > 0}
                      onChange={handleSelectAll}
                      style={{ cursor: 'pointer' }}
                    />
                  </th>
                  <th style={{ padding: '10px 14px', textAlign: 'left', color: '#94a3b8', fontSize: '12px', fontWeight: 600 }}>
                    Data Point
                  </th>
                  <th style={{ padding: '10px 14px', textAlign: 'left', color: '#94a3b8', fontSize: '12px', fontWeight: 600 }}>
                    Entity
                  </th>
                  <th style={{ padding: '10px 14px', textAlign: 'left', color: '#94a3b8', fontSize: '12px', fontWeight: 600 }}>
                    Endpoint
                  </th>
                  <th style={{ padding: '10px 14px', textAlign: 'center', color: '#94a3b8', fontSize: '12px', fontWeight: 600 }}>
                    Fields
                  </th>
                  <th style={{ padding: '10px 14px', textAlign: 'center', color: '#94a3b8', fontSize: '12px', fontWeight: 600 }}>
                    Status
                  </th>
                  <th style={{ padding: '10px 14px', textAlign: 'left', color: '#94a3b8', fontSize: '12px', fontWeight: 600 }}>
                    Confirmed
                  </th>
                  <th style={{ padding: '10px 14px', textAlign: 'right', color: '#94a3b8', fontSize: '12px', fontWeight: 600 }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {mappings.map(m => {
                  const isSelected = selectedIds.has(m.id);
                  const allApproved = m.flagged_count === 0;
                  return (
                    <tr key={m.id} style={{
                      borderBottom: '1px solid #1e293b',
                      background: isSelected ? '#1e3a5f' : 'transparent',
                    }}>
                      <td style={{ padding: '10px 14px', textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleSelect(m.id)}
                          style={{ cursor: 'pointer' }}
                        />
                      </td>
                      <td style={{ padding: '10px 14px', color: '#f1f5f9', fontSize: '13px', fontWeight: 500 }}>
                        {m.data_point}
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <span style={{
                          padding: '2px 8px', borderRadius: '12px',
                          background: '#1e3a5f', color: '#93c5fd',
                          fontSize: '12px', fontWeight: 600,
                        }}>
                          {m.cmsd_entity}
                        </span>
                        {(m.relation_count ?? 0) > 0 && (
                          <span style={{
                            padding: '2px 8px', borderRadius: '12px',
                            background: '#312e81', color: '#a5b4fc',
                            fontSize: '11px', fontWeight: 600, marginLeft: '6px',
                          }}>
                            🔗 {m.relation_count}
                          </span>
                        )}
                      </td>
                      <td style={{ padding: '10px 14px', color: '#94a3b8', fontSize: '12px', fontFamily: 'monospace' }}>
                        {m.source?.endpoint || '—'}
                      </td>
                      <td style={{ padding: '10px 14px', textAlign: 'center', color: '#e2e8f0', fontSize: '12px' }}>
                        {m.approved_count}/{m.field_count}
                      </td>
                      <td style={{ padding: '10px 14px', textAlign: 'center' }}>
                        <span style={{
                          padding: '2px 8px', borderRadius: '10px', fontSize: '11px', fontWeight: 600,
                          background: allApproved ? '#064e3b' : '#78350f',
                          color: allApproved ? '#6ee7b7' : '#fbbf24',
                        }}>
                          {allApproved ? 'Ready' : `${m.flagged_count} flagged`}
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px', color: '#64748b', fontSize: '11px' }}>
                        {formatDate(m.confirmed_at)}
                      </td>
                      <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                          <button
                            onClick={() => handleEdit(m)}
                            style={{
                              padding: '4px 10px', borderRadius: '4px',
                              background: '#1e3a5f', border: 'none', color: '#93c5fd',
                              cursor: 'pointer', fontSize: '11px',
                            }}
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDelete(m.id)}
                            style={{
                              padding: '4px 10px', borderRadius: '4px',
                              background: '#7f1d1d', border: 'none', color: '#fca5a5',
                              cursor: 'pointer', fontSize: '11px',
                            }}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Bottom bar */}
          <div style={{
            marginTop: '16px', padding: '12px 16px', background: '#1e293b',
            borderRadius: '8px', border: '1px solid #334155',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span style={{ color: '#94a3b8', fontSize: '13px' }}>
              {selectedIds.size} mapping(s) selected
            </span>
            <button
              onClick={handleGenerate}
              disabled={selectedIds.size === 0}
              style={{
                padding: '10px 24px', borderRadius: '8px',
                background: selectedIds.size > 0 ? '#7c3aed' : '#334155',
                border: 'none', color: selectedIds.size > 0 ? '#fff' : '#64748b',
                cursor: selectedIds.size > 0 ? 'pointer' : 'default',
                fontWeight: 600, fontSize: '14px',
              }}
            >
              Generate & Apply
            </button>
          </div>
        </>
      )}

      {/* Dependency Auto-Select Prompt */}
      {showDepsPrompt && depsPromptInfo && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.7)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div style={{
            background: '#1e293b', borderRadius: '12px', border: '1px solid #334155',
            padding: '24px', width: '480px',
          }}>
            <h3 style={{ color: '#f1f5f9', margin: '0 0 12px', fontSize: '16px' }}>
              Missing Dependencies
            </h3>
            <div style={{ color: '#94a3b8', fontSize: '13px', marginBottom: '16px' }}>
              {depsPromptInfo.missing.map((m: any, i: number) => {
                const forMapping = mappings.find(mp => mp.id === m.for_mapping);
                const needsMapping = mappings.find(mp => mp.id === m.needs);
                const isRelation = m.is_relation;
                return (
                  <div key={i} style={{
                    marginBottom: '8px', padding: '8px 10px', borderRadius: '6px',
                    background: isRelation ? '#1e1b4b' : 'transparent',
                    border: isRelation ? '1px solid #3730a3' : 'none',
                  }}>
                    {isRelation ? (
                      <>
                        <span style={{ fontSize: '10px', color: '#818cf8', fontWeight: 600, textTransform: 'uppercase' }}>Relation</span>
                        <br />
                        <strong style={{ color: '#f1f5f9' }}>"{forMapping?.data_point || m.for_entity}"</strong>
                        {' '}({m.for_entity}) references{' '}
                        <strong style={{ color: '#f1f5f9' }}>{m.needs_entity}</strong>
                        {' '}via <code style={{ color: '#c7d2fe', fontSize: '10px' }}>{m.relation_path}</code>
                      </>
                    ) : (
                      <>
                        <strong style={{ color: '#f1f5f9' }}>"{forMapping?.data_point || m.for_entity}"</strong>
                        {' '}({m.for_entity}) depends on{' '}
                        <strong style={{ color: '#f1f5f9' }}>"{needsMapping?.data_point || m.needs_entity}"</strong>
                        {' '}({m.needs_entity})
                      </>
                    )}
                    {needsMapping ? (
                      <span style={{ color: '#6ee7b7', fontSize: '11px', marginLeft: '6px' }}>— exists, not selected</span>
                    ) : (
                      <span style={{ color: '#fca5a5', fontSize: '11px', marginLeft: '6px' }}>— mapping does not exist yet</span>
                    )}
                  </div>
                );
              })}
              {depsPromptInfo.autoSelectIds.filter(id => mappings.some(m => m.id === id)).length > 0 && (
                <p style={{ color: '#93c5fd', fontSize: '12px', marginTop: '12px' }}>
                  Auto-select {depsPromptInfo.autoSelectIds.length} additional mapping(s) to resolve dependencies?
                </p>
              )}
            </div>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button onClick={handleDeclineAutoSelect} style={{
                padding: '8px 16px', borderRadius: '6px',
                background: '#334155', border: 'none', color: '#94a3b8',
                cursor: 'pointer', fontSize: '13px',
              }}>
                Cancel
              </button>
              <button onClick={handleAcceptAutoSelect}
                disabled={depsPromptInfo.autoSelectIds.every(id => !mappings.some(m => m.id === id))}
                style={{
                  padding: '8px 16px', borderRadius: '6px',
                  background: depsPromptInfo.autoSelectIds.every(id => !mappings.some(m => m.id === id)) ? '#334155' : '#7c3aed',
                  border: 'none',
                  color: depsPromptInfo.autoSelectIds.every(id => !mappings.some(m => m.id === id)) ? '#64748b' : '#fff',
                  cursor: depsPromptInfo.autoSelectIds.every(id => !mappings.some(m => m.id === id)) ? 'not-allowed' : 'pointer',
                  fontSize: '13px', fontWeight: 600,
                }}>
                Auto-select & Continue
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Pre-flight loading overlay */}
      {preflightLoading && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 999,
        }}>
          <div style={{
            background: '#1e293b', borderRadius: '12px', padding: '24px',
            display: 'flex', alignItems: 'center', gap: '12px',
          }}>
            <span style={{ display: 'inline-block', width: '20px', height: '20px', border: '2px solid #3b82f6', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.6s linear infinite' }} />
            <span style={{ color: '#94a3b8', fontSize: '14px' }}>Running pre-flight check...</span>
          </div>
          <style>{'@keyframes spin { to { transform: rotate(360deg); } }'}</style>
        </div>
      )}

      {/* Generate Modal */}
      <GenerateModal
        open={generateOpen}
        mappingIds={generateIds}
        onClose={() => { setGenerateOpen(false); setPreflightResult(null); }}
        onComplete={(_report: RefreshReport) => { loadMappings(); }}
        onViewDashboard={onViewDashboard}
        preflightResult={preflightResult}
      />
    </div>
  );
}
