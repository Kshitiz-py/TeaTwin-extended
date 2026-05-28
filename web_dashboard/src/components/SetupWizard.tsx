import { useState, useEffect } from 'react';
import AgentConnect from './AgentConnect';
import ConnectSources from './ConnectSources';
import MappingWizard from './MappingWizard';
import ReviewQueue from './ReviewQueue';
import { SourceData } from './SourceCard';
import { agentApi, AgentStatus } from '../services/agentApi';

const STEPS = [
  { key: 'llm'       as const, label: 'Connect LLM',        icon: '🤖' },
  { key: 'connect'   as const, label: 'Connect Sources',    icon: '🔗' },
  { key: 'explorer'  as const, label: 'API Explorer',       icon: '🔍' },
  { key: 'queue'     as const, label: 'Review Queue',       icon: '📋' },
];

interface SetupWizardProps {
  onLaunch: () => void;
  onDisconnected?: () => void;
  devMode?: boolean;
  initialStep?: number;
}

export default function SetupWizard({ onLaunch, onDisconnected, devMode = false, initialStep = 0 }: SetupWizardProps) {
  const [activeStep, setActiveStep] = useState(initialStep);
  const [sources, setSources] = useState<SourceData[]>([]);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [llmConnected, setLlmConnected] = useState(false);
  const [preloadedMapping, setPreloadedMapping] = useState<any>(null);

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
    // Don't auto-navigate — user uses "→ Connect Sources" button instead
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
            Connect LLM → Configure Sources → Map APIs → Review & Generate
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
          <AgentConnect onConnected={handleLlmConnected} onDisconnected={handleLlmDisconnected} onNavigateToSources={() => setActiveStep(1)} />
        )}
        {step.key === 'connect' && (
          <ConnectSources
            onSourcesComplete={handleSourcesComplete}
            agentConnected={llmConnected}
          />
        )}
        {step.key === 'explorer' && (
          <MappingWizard
            onNavigateToQueue={() => { setActiveStep(3); setPreloadedMapping(null); }}
            preloadedMapping={preloadedMapping}
            onClearPreloaded={() => setPreloadedMapping(null)}
            devMode={devMode}
          />
        )}
        {step.key === 'queue' && (
          <ReviewQueue
            embedded
            onViewDashboard={onLaunch}
            onEdit={async (mappingId) => {
              try {
                const full = await agentApi.getMapping(mappingId);
                setPreloadedMapping(full);
                setActiveStep(2);
              } catch { setActiveStep(2); }
            }}
            onNavigateToExplorer={() => { setPreloadedMapping(null); setActiveStep(2); }}
          />
        )}
      </div>
    </div>
  );
}
