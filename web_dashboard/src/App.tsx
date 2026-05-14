import { useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import FactoryTopology from './components/FactoryTopology';
import ResourcePanel from './components/ResourcePanel';
import OrderTracker from './components/OrderTracker';
import ChangeLog from './components/ChangeLog';
import { api } from './services/api';

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

const statusColor = (s: string | null): string => {
  if (!s) return '#94a3b8';
  switch (s) {
    case 'busy': return '#3b82f6';
    case 'idle': return '#22c55e';
    case 'broken': return '#ef4444';
    case 'setup': return '#f59e0b';
    case 'paused': return '#94a3b8';
    case 'underMaintenance': return '#a855f7';
    case 'charging': return '#06b6d4';
    default: return '#94a3b8';
  }
};

export default function App() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [activeTab, setActiveTab] = useState<'topology' | 'resources' | 'orders' | 'changes'>('topology');
  const { events, connected } = useWebSocket();

  useEffect(() => {
    api.getSummary().then(setSummary).catch(console.error);
    const interval = setInterval(() => {
      api.getSummary().then(setSummary).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const tabs = [
    { key: 'topology' as const, label: 'Factory Topology' },
    { key: 'resources' as const, label: 'Resources' },
    { key: 'orders' as const, label: 'Orders' },
    { key: 'changes' as const, label: `Change Log (${events.length})` },
  ];

  return (
    <div style={{ minHeight: '100vh' }}>
      {/* Header */}
      <header style={{
        background: '#1e293b', padding: '12px 24px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: '1px solid #334155',
      }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#f1f5f9' }}>
            CMSD Digital Twin — Factory Dashboard
          </h1>
          <p style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
            SAP/MES → CMSD Twin | Poll #{summary?.poll_count ?? 0} | 
            Changes: {summary?.total_changes ?? 0}
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
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
        </div>
      </header>

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
      </div>
    </div>
  );
}