import { useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import FactoryTopology from './components/FactoryTopology';
import ResourcePanel from './components/ResourcePanel';
import OrderTracker from './components/OrderTracker';
import ChangeLog from './components/ChangeLog';
import SetupWizard from './components/SetupWizard';
import ReviewQueue from './components/ReviewQueue';
import AgentConnect from './components/AgentConnect';
import { api } from './services/api';
import { agentApi, AgentStatus } from './services/agentApi';

type AppMode = 'dashboard' | 'wizard';

interface Summary {
  resources: number;
  resource_classes: number;
  part_types: number;
  orders: number;
  jobs: number;
  calendars: number;
  connections: number;
  poll_count: number;
  total_changes: number;
  last_poll_time: string | null;
  status: string;
}

export default function App() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [activeTab, setActiveTab] = useState<'topology' | 'resources' | 'orders' | 'changes' | 'mappings'>('topology');
  const [activeMode, setActiveMode] = useState<AppMode>('dashboard');
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [sourceCount, setSourceCount] = useState(0);
  const [initialCheckDone, setInitialCheckDone] = useState(false);
  const { events, connected } = useWebSocket();

  // Refresh controls (5.5)
  const [refreshStatus, setRefreshStatus] = useState<{
    is_polling: boolean;
    poll_interval_seconds: number;
    last_refreshed: string | null;
    mappings_loaded: number;
  } | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<string | null>(null);

  // Global dev mode — controls hardcoded factory visibility
  const [devMode, setDevMode] = useState(() => {
    try { return localStorage.getItem('cmsd_dev_mode') === 'true'; } catch { return false; }
  });
  const toggleDevMode = () => {
    const next = !devMode;
    setDevMode(next);
    try { localStorage.setItem('cmsd_dev_mode', String(next)); } catch {}
  };
  const [hardcodedLoaded, setHardcodedLoaded] = useState(() => {
    try { return sessionStorage.getItem('hardcoded_loaded') === 'true'; } catch { return false; }
  });
  const [initialWizardStep, setInitialWizardStep] = useState(0);

  // ─── Initialisation: check agent status + source count ───
  useEffect(() => {
    let agentOk = false;
    let sourcesOk = false;

    const maybeDone = () => {
      if (agentOk !== undefined && sourcesOk !== undefined) {
        setInitialCheckDone(true);
      }
    };

    // Check agent
    agentApi.getAgentStatus()
      .then(s => {
        setAgentStatus(s);
        agentOk = true;
      })
      .catch(() => {
        setAgentStatus(null);
        agentOk = false;
      })
      .finally(maybeDone);

    // Check sources
    agentApi.getSources()
      .then(data => {
        const count = data?.sources?.length ?? 0;
        setSourceCount(count);
        sourcesOk = true;
        // Option C: if no sources configured, force wizard mode
        if (count === 0) {
          setActiveMode('wizard');
        }
      })
      .catch(() => {
        setSourceCount(0);
        sourcesOk = false;
        setActiveMode('wizard');
      })
      .finally(maybeDone);
  }, []);

  // ─── Poll summary only when dashboard is active AND sources exist ───
  useEffect(() => {
    if (activeMode === 'dashboard' && sourceCount > 0) {
      api.getSummary().then(setSummary).catch(console.error);
      const interval = setInterval(() => {
        api.getSummary().then(setSummary).catch(() => {});
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [activeMode, sourceCount]);

  // WebSocket-driven immediate summary refresh (5.5)
  useEffect(() => {
    if (events.length > 0 && activeMode === 'dashboard') {
      api.getSummary().then(setSummary).catch(() => {});
    }
  }, [events.length, activeMode]);

  // Refresh agent status periodically
  useEffect(() => {
    const interval = setInterval(() => {
      agentApi.getAgentStatus()
        .then(setAgentStatus)
        .catch(() => setAgentStatus(null));
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  // Refresh status polling (5.5)
  useEffect(() => {
    if (activeMode !== 'dashboard') return;
    api.getRefreshStatus().then(s => {
      setRefreshStatus(s);
      if (s.last_refreshed) setLastRefreshed(s.last_refreshed);
    }).catch(() => {});
    const interval = setInterval(() => {
      api.getRefreshStatus().then(s => {
        setRefreshStatus(s);
        if (s.last_refreshed) setLastRefreshed(s.last_refreshed);
      }).catch(() => {});
    }, 10000);
    return () => clearInterval(interval);
  }, [activeMode]);

  // Manual refresh handler
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const report = await api.refreshInstances();
      setLastRefreshed(report.refreshed_at);
    } catch (e: any) {
      console.error('Refresh failed:', e);
    } finally {
      setRefreshing(false);
    }
  };

  // Polling toggle
  const handlePollingToggle = async (enable: boolean) => {
    const interval = enable ? 30 : 0;
    await api.setPolling(interval);
    setRefreshStatus(prev => prev ? { ...prev, is_polling: enable, poll_interval_seconds: interval } : null);
  };

  const toggleMode = () => {
    if (activeMode === 'wizard' && sourceCount === 0) return;
    if (activeMode === 'dashboard') setInitialWizardStep(0);  // reset step on manual toggle
    setActiveMode(activeMode === 'dashboard' ? 'wizard' : 'dashboard');
  };

  const handleAgentConnected = () => {
    agentApi.getAgentStatus()
      .then(setAgentStatus)
      .catch(() => {});
  };

  const handleAgentDisconnected = () => {
    setAgentStatus({
      connected: false,
    });
  };

  const handleSetupComplete = () => {
    // Re-check source count after setup
    agentApi.getSources()
      .then(data => {
        const count = data?.sources?.length ?? 0;
        setSourceCount(count);
        if (count > 0) {
          setActiveMode('dashboard');
        }
      })
      .catch(() => {});
  };

  const tabs = [
    { key: 'topology' as const, label: 'Factory Topology' },
    { key: 'resources' as const, label: 'Resources' },
    { key: 'orders' as const, label: 'Orders' },
    { key: 'changes' as const, label: `Change Log (${events.length})` },
    { key: 'mappings' as const, label: 'Mapping Registry' },
  ];

  const agentOnline = agentStatus?.connected ?? false;

  // ─── Loading spinner ─────────────────────────────────────

  if (!initialCheckDone) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#0f172a', color: '#94a3b8', fontSize: '14px',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '40px', height: '40px', margin: '0 auto 16px',
            border: '3px solid #334155', borderTopColor: '#3b82f6', borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }} />
          <style>{'@keyframes spin { to { transform: rotate(360deg); } }'}</style>
          Checking system status...
        </div>
      </div>
    );
  }

  // ─── Shared Header ─────────────────────────────────────

  const modeToggleButton = (
    <button
      onClick={toggleMode}
      disabled={activeMode === 'wizard' && sourceCount === 0}
      title={activeMode === 'wizard' && sourceCount === 0 ? 'Configure at least one data source first' : ''}
      style={{
        padding: '6px 16px', borderRadius: '6px', border: '1px solid #475569',
        background: (activeMode === 'wizard' && sourceCount === 0) ? '#1e293b' : '#1e293b',
        color: (activeMode === 'wizard' && sourceCount === 0) ? '#64748b' : '#e2e8f0',
        cursor: (activeMode === 'wizard' && sourceCount === 0) ? 'not-allowed' : 'pointer',
        fontSize: '13px', fontWeight: 500,
        display: 'flex', alignItems: 'center', gap: '6px',
        opacity: (activeMode === 'wizard' && sourceCount === 0) ? 0.5 : 1,
      }}
    >
      {activeMode === 'dashboard' ? (
        <><span>⚙️</span> Setup Wizard</>
      ) : (
        <><span>📊</span> Dashboard</>
      )}
    </button>
  );

  const sharedHeader = (title: string, subtitle: string) => (
    <header style={{
      background: '#1e293b', padding: '12px 24px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      borderBottom: '1px solid #334155',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        {modeToggleButton}
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#f1f5f9', margin: 0 }}>
            {title}
          </h1>
          <p style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
            {subtitle}
          </p>
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Agent status pill */}
        <span style={{
          padding: '4px 10px', borderRadius: '12px', fontSize: '12px',
          background: agentOnline ? '#064e3b' : agentStatus === null ? '#7f1d1d' : '#78350f',
          color: agentOnline ? '#6ee7b7' : agentStatus === null ? '#fca5a5' : '#fbbf24',
        }}>
          <span style={{
            display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%',
            background: agentOnline ? '#22c55e' : agentStatus === null ? '#ef4444' : '#f59e0b',
            boxShadow: agentOnline ? '0 0 6px #22c55e' : '0 0 6px #ef4444',
            marginRight: '4px',
          }} />
          Agent {agentOnline ? 'Online' : agentStatus === null ? 'Offline' : 'Unconfigured'}
        </span>
        {/* Source count pill */}
        <span style={{
          padding: '4px 10px', borderRadius: '12px', fontSize: '12px',
          background: sourceCount > 0 ? '#064e3b' : '#7f1d1d',
          color: sourceCount > 0 ? '#6ee7b7' : '#fca5a5',
        }}>
          {sourceCount > 0 ? `📡 ${sourceCount} Source${sourceCount > 1 ? 's' : ''}` : '📡 No Sources'}
        </span>
        {/* Dev mode toggle — always visible */}
        <span onClick={toggleDevMode}
          title={devMode ? 'Dev mode ON — hardcoded factory available' : 'Dev mode OFF — mapping-driven only'}
          style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', fontSize: '10px', color: devMode ? '#a5b4fc' : '#475569', userSelect: 'none' }}>
          <span style={{ display: 'inline-block', width: '22px', height: '12px', borderRadius: '6px', background: devMode ? '#4f46e5' : '#334155', position: 'relative', transition: 'background 0.2s' }}>
            <span style={{ position: 'absolute', top: '1px', left: devMode ? '11px' : '1px', width: '10px', height: '10px', borderRadius: '50%', background: '#fff', transition: 'left 0.2s' }} />
          </span>
          Dev
        </span>
        {activeMode === 'dashboard' && (
          <>
            <span style={{ color: '#334155' }}>|</span>
            <span style={{
              padding: '4px 12px', borderRadius: '12px', fontSize: '12px',
              background: connected ? '#064e3b' : '#7f1d1d',
              color: connected ? '#6ee7b7' : '#fca5a5',
            }}>
              {connected ? 'WS Live' : 'WS Offline'}
            </span>
            <span style={{ fontSize: '12px', color: '#94a3b8' }}>
              Last poll: {summary?.last_poll_time
                ? new Date(summary.last_poll_time).toLocaleTimeString()
                : '...'}
            </span>
          </>
        )}
      </div>
    </header>
  );

  // ─── Wizard Mode ───────────────────────────────────────

  if (activeMode === 'wizard') {
    return (
      <div style={{ minHeight: '100vh', background: '#0f172a', color: '#f1f5f9' }}>
        {sharedHeader(
          'CMSD Digital Twin — Setup Wizard',
          'AI-guided API to CMSD mapping — connect agent, configure sources, map, review'
        )}

        <SetupWizard onLaunch={handleSetupComplete} onDisconnected={handleAgentDisconnected} devMode={devMode} initialStep={initialWizardStep} />
      </div>
    );
  }

  // ─── Dashboard Mode ──────────────────────────────────────

  // Block dashboard if no sources configured
  if (sourceCount === 0) {
    return (
      <div style={{ minHeight: '100vh', background: '#0f172a', color: '#f1f5f9' }}>
        {sharedHeader(
          'CMSD Digital Twin — Factory Dashboard',
          'No data sources configured'
        )}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', padding: '24px' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📡</div>
          <h2 style={{ color: '#f1f5f9', fontSize: '22px', margin: '0 0 8px' }}>No Data Sources Configured</h2>
          <p style={{ color: '#94a3b8', fontSize: '14px', margin: '0 0 24px', textAlign: 'center', maxWidth: '400px' }}>
            The digital twin dashboard requires at least one data source to build the factory model.
            Use the Setup Wizard to connect your SAP and MES APIs.
          </p>
          <button
            onClick={() => setActiveMode('wizard')}
            style={{
              padding: '12px 24px', borderRadius: '8px', border: 'none', cursor: 'pointer',
              background: '#2563eb', color: '#f1f5f9', fontSize: '15px', fontWeight: 600,
            }}
          >
            ⚙️ Open Setup Wizard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh' }}>
      {sharedHeader(
        'CMSD Digital Twin — Factory Dashboard',
        `SAP/MES → CMSD Twin | Poll #${summary?.poll_count ?? 0} | Changes: ${summary?.total_changes ?? 0}`
      )}

      {/* Warning bar if agent is offline */}
      {!agentOnline && (
        <div style={{
          background: '#78350f', color: '#fbbf24', padding: '8px 24px',
          fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px',
          borderBottom: '1px solid #92400e',
        }}>
          <span>⚠️</span>
          AI Agent is offline — RAG-powered mapping and code generation are unavailable.
          Use the Setup Wizard to connect your Ollama agent.
        </div>
      )}

      {/* Simulated data banner */}
      {devMode && (
        <div style={{
          background: '#422006', color: '#fde68a', padding: '6px 24px',
          fontSize: '12px', display: 'flex', alignItems: 'center', gap: '10px',
          borderBottom: '1px solid #78350f',
        }}>
          <span>🔧</span>
          {hardcodedLoaded
            ? 'Hardcoded factory loaded alongside mapping-driven instances.'
            : 'Dev mode active — load hardcoded factory to see all mock data.'}
          <button onClick={async () => {
            if (hardcodedLoaded) {
              try { await api.refreshInstances(undefined, false); } catch {}
              try { sessionStorage.setItem('hardcoded_loaded', 'false'); } catch {}
              setHardcodedLoaded(false);
              window.location.reload();
            } else {
              try { await api.refreshInstances(undefined, true); } catch {}
              try { sessionStorage.setItem('hardcoded_loaded', 'true'); } catch {}
              setHardcodedLoaded(true);
              window.location.reload();
            }
          }}
            style={{ padding: '3px 10px', borderRadius: '4px', border: '1px solid #f59e0b', background: hardcodedLoaded ? '#7f1d1d' : '#78350f', color: '#fde68a', cursor: 'pointer', fontSize: '11px', fontWeight: 600, whiteSpace: 'nowrap' }}>
            {hardcodedLoaded ? 'Unload Hardcoded' : 'Load Hardcoded'}
          </button>
        </div>
      )}
      {!devMode && (
        <div style={{
          background: '#1e3a5f', color: '#93c5fd', padding: '8px 24px',
          fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px',
          borderBottom: '1px solid #1e40af',
        }}>
          <span>📢</span>
          Mapping-driven mode — only confirmed mappings generate instances. Toggle Dev to load hardcoded factory.
        </div>
      )}

      {/* KPI Cards */}
      {summary && (
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
          gap: '12px', padding: '16px 24px',
        }}>
          {[
            { label: 'Resources', value: summary.resources },
            { label: 'Resource Classes', value: summary.resource_classes },
            { label: 'Part Types', value: summary.part_types },
            { label: 'Orders', value: summary.orders },
            { label: 'Jobs', value: summary.jobs },
            { label: 'Connections', value: summary.connections },
          ].map(kpi => (
            <div key={kpi.label} style={{
              background: '#1e293b', borderRadius: '8px', padding: '14px',
              border: '1px solid #334155',
            }}>
              <p style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>{kpi.label}</p>
              <p style={{ fontSize: '28px', fontWeight: 700, color: '#f1f5f9' }}>{kpi.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Refresh Controls Toolbar (5.5) */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '16px',
        padding: '10px 24px', borderBottom: '1px solid #334155',
      }}>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          style={{
            padding: '8px 16px', borderRadius: '6px', border: '1px solid #475569',
            background: refreshing ? '#1e293b' : '#0f172a',
            color: refreshing ? '#64748b' : '#93c5fd',
            cursor: refreshing ? 'not-allowed' : 'pointer',
            fontSize: '13px', fontWeight: 600,
          }}
        >
          {refreshing ? '⟳ Refreshing...' : '↻ Refresh Data'}
        </button>

        {lastRefreshed && (
          <span style={{ fontSize: '12px', color: '#64748b' }}>
            Last: {new Date(lastRefreshed).toLocaleTimeString()}
          </span>
        )}

        <span style={{ color: '#334155' }}>|</span>

        <label style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          fontSize: '13px', color: '#94a3b8', cursor: 'pointer',
        }}>
          <span>Auto-refresh</span>
          <button
            onClick={() => handlePollingToggle(!refreshStatus?.is_polling)}
            style={{
              width: '40px', height: '22px', borderRadius: '11px',
              border: 'none',
              background: refreshStatus?.is_polling ? '#22c55e' : '#334155',
              cursor: 'pointer', position: 'relative',
              transition: 'background 0.2s',
            }}
          >
            <span style={{
              position: 'absolute', top: '2px',
              left: refreshStatus?.is_polling ? '20px' : '2px',
              width: '18px', height: '18px', borderRadius: '50%',
              background: '#fff', transition: 'left 0.2s',
            }} />
          </button>
        </label>

        {refreshStatus?.is_polling && (
          <select
            value={refreshStatus.poll_interval_seconds}
            onChange={(e) => {
              const val = parseInt(e.target.value);
              api.setPolling(val);
            }}
            style={{
              padding: '4px 8px', borderRadius: '4px',
              background: '#1e293b', border: '1px solid #475569',
              color: '#e2e8f0', fontSize: '12px',
            }}
          >
            <option value={10}>10s</option>
            <option value={30}>30s</option>
            <option value={60}>60s</option>
            <option value={300}>5m</option>
          </select>
        )}

        <span style={{
          marginLeft: 'auto', fontSize: '12px',
          color: refreshStatus?.is_polling ? '#22c55e' : '#64748b',
        }}>
          {refreshStatus?.is_polling ? '● Live' : '○ Manual'}
        </span>
      </div>

      {/* Tab Bar */}
      <div style={{
        padding: '0 24px', display: 'flex', gap: '4px',
        borderBottom: '1px solid #334155',
      }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '10px 20px', border: 'none', cursor: 'pointer',
              background: activeTab === tab.key ? '#334155' : 'transparent',
              color: activeTab === tab.key ? '#f1f5f9' : '#94a3b8',
              borderRadius: '6px 6px 0 0', fontSize: '13px', fontWeight: 500,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ padding: '16px 24px' }}>
        {activeTab === 'topology' && <FactoryTopology events={events} />}
        {activeTab === 'resources' && <ResourcePanel />}
        {activeTab === 'orders' && <OrderTracker />}
        {activeTab === 'changes' && <ChangeLog events={events} />}
        {activeTab === 'mappings' && (
          <ReviewQueue
            embedded={false}
            onNavigateToExplorer={() => { setInitialWizardStep(2); setActiveMode('wizard'); }}
          />
        )}
      </div>
    </div>
  );
}
