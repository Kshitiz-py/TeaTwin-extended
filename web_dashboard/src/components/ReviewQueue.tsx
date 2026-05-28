import { useState, useEffect, useCallback } from 'react';
import { agentApi, MappingSummary } from '../services/agentApi';
import GenerateModal from './GenerateModal';
import { RefreshReport } from '../services/api';

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

  const handleGenerate = () => {
    if (selectedIds.size > 0) {
      setGenerateIds(Array.from(selectedIds));
      setGenerateOpen(true);
      onGenerate?.(Array.from(selectedIds));
    }
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

      {/* Generate Modal */}
      <GenerateModal
        open={generateOpen}
        mappingIds={generateIds}
        onClose={() => setGenerateOpen(false)}
        onComplete={(_report: RefreshReport) => { loadMappings(); }}
        onViewDashboard={onViewDashboard}
      />
    </div>
  );
}
