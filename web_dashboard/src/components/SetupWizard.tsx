import { useState, useEffect } from 'react';
import AgentConnect from './AgentConnect';
import ConnectSources from './ConnectSources';
import MappingWizard from './MappingWizard';
import ManualBuilder from './ManualBuilder';
import ReviewQueue from './ReviewQueue';
import { SourceData } from './SourceCard';
import { agentApi, AgentStatus } from '../services/agentApi';

const STEPS = [
  { key: 'llm'       as const, label: 'Connect LLM',        dot: '#8b5cf6', num: 1 },
  { key: 'connect'   as const, label: 'Connect Sources',    dot: '#3b82f6', num: 2 },
  { key: 'explorer'  as const, label: 'Guided Builder',     dot: '#6366f1', num: 3 },
  { key: 'manuals'   as const, label: 'Manual Builder',     dot: '#f59e0b', num: 4 },
  { key: 'queue'     as const, label: 'Review Queue',       dot: '#22c55e', num: 5 },
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
  const [manualPreset, setManualPreset] = useState<{ entityType: string; identifiers: string[] } | null>(null);

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

  const handleLlmConnected = () => { setLlmConnected(true); };
  const handleLlmDisconnected = () => {
    setLlmConnected(false);
    setAgentStatus({ connected: false });
    onDisconnected?.();
  };
  const handleSourcesComplete = (connectedSources: SourceData[]) => {
    setSources(connectedSources);
    setActiveStep(2);
  };

  const step = STEPS[activeStep];

  const StepBtn = ({ idx }: { idx: number }) => {
    const s = STEPS[idx];
    const isActive = idx === activeStep;
    return (
      <button
        onClick={() => setActiveStep(idx)}
        style={{
          padding: '10px 18px', borderRadius: '10px', border: '1.5px solid',
          borderColor: isActive ? s.dot : 'transparent',
          background: isActive
            ? `linear-gradient(135deg, ${s.dot}18, ${s.dot}08)`
            : 'transparent',
          color: isActive ? '#f1f5f9' : '#64748b',
          cursor: 'pointer', fontSize: '12px', fontWeight: 500,
          display: 'inline-flex', alignItems: 'center', gap: '8px',
          transition: 'all 0.2s ease', whiteSpace: 'nowrap',
          letterSpacing: '0.01em',
        }}
        onMouseEnter={e => {
          if (!isActive) {
            e.currentTarget.style.color = '#94a3b8';
            e.currentTarget.style.borderColor = '#334155';
          }
        }}
        onMouseLeave={e => {
          if (!isActive) {
            e.currentTarget.style.color = '#64748b';
            e.currentTarget.style.borderColor = 'transparent';
          }
        }}
      >
        <span style={{
          width: '22px', height: '22px', borderRadius: '50%',
          background: isActive ? s.dot : '#1e293b',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '10px', fontWeight: 700, color: isActive ? '#fff' : '#475569',
          flexShrink: 0, border: isActive ? 'none' : '1px solid #334155',
          boxShadow: isActive ? `0 0 10px ${s.dot}60` : 'none',
          transition: 'all 0.2s ease',
        }}>{s.num}</span>
        <span>{s.label}</span>
      </button>
    );
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a' }}>
      <header style={{
        background: 'linear-gradient(180deg, #1a1f2e 0%, #111827 100%)',
        padding: '16px 28px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: '1px solid #1e293b',
      }}>
        <div>
          <h1 style={{
            fontSize: '18px', fontWeight: 600, color: '#f1f5f9', margin: 0,
            letterSpacing: '-0.02em',
          }}>
            CMSD Digital Twin <span style={{ color: '#475569', fontWeight: 400 }}>/</span> Setup
          </h1>
          <p style={{ fontSize: '11px', color: '#475569', marginTop: '3px', letterSpacing: '0.02em' }}>
            Connect LLM  ·  Configure Sources  ·  Guided Builder  ·  Manual Builder  ·  Review & Generate
          </p>
        </div>
        {agentStatus?.connected ? (
          <span style={{
            padding: '5px 14px', borderRadius: '20px', fontSize: '11px', fontWeight: 500,
            background: '#064e3b', color: '#6ee7b7', border: '1px solid #065f46',
            display: 'flex', alignItems: 'center', gap: '6px',
          }}>
            <span style={{
              width: '6px', height: '6px', borderRadius: '50%', background: '#22c55e',
              boxShadow: '0 0 6px #22c55e80', flexShrink: 0,
            }} />
            {agentStatus.provider_type ?? 'LLM'} · {agentStatus.chat_model}
          </span>
        ) : (
          <span style={{
            padding: '5px 14px', borderRadius: '20px', fontSize: '11px', fontWeight: 500,
            background: '#7f1d1d', color: '#fca5a5', border: '1px solid #991b1b',
            display: 'flex', alignItems: 'center', gap: '6px',
          }}>
            <span style={{
              width: '6px', height: '6px', borderRadius: '50%', background: '#ef4444',
              flexShrink: 0,
            }} />
            LLM not connected
          </span>
        )}
      </header>

      {/* Stepper */}
      <div style={{
        padding: '20px 32px 16px',
        background: 'linear-gradient(180deg, #0f172a 0%, #0a0f1a 100%)',
        borderBottom: '1px solid #1e293b',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0',
        }}>
          {/* Steps 1 and 2 */}
          <StepBtn idx={0} />
          <div style={{
            width: '32px', height: '1.5px', background: '#1e293b', margin: '0 6px', flexShrink: 0,
            borderRadius: '1px',
          }} />
          <StepBtn idx={1} />
          <div style={{
            width: '32px', height: '1.5px', background: '#1e293b', margin: '0 6px', flexShrink: 0,
            borderRadius: '1px',
          }} />

          {/* Steps 3-4-5 group with skip pipe */}
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            {/* Skip pipe overlay */}
            <svg
              viewBox="0 0 100 28"
              preserveAspectRatio="none"
              style={{
                position: 'absolute', top: '-11px', left: 0, width: '100%', height: '28px',
                overflow: 'visible', pointerEvents: 'none',
              }}
            >
              <path
                d="M 33,28 L 33,2 L 67,2 L 67,28"
                stroke="#334155"
                strokeWidth="1.5"
                fill="none"
                strokeLinecap="butt"
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
                opacity="0.6"
              />
            </svg>

            <StepBtn idx={2} />
            <div style={{
              width: '32px', height: '1.5px', background: '#1e293b', margin: '0 6px', flexShrink: 0,
              borderRadius: '1px',
            }} />
            <StepBtn idx={3} />
            <div style={{
              width: '32px', height: '1.5px', background: '#1e293b', margin: '0 6px', flexShrink: 0,
              borderRadius: '1px',
            }} />
            <StepBtn idx={4} />
          </div>
        </div>

      </div>

      {/* Step Content */}
      <div style={{ padding: '28px 32px' }}>
        {step.key === 'llm' && (
          <AgentConnect onConnected={handleLlmConnected} onDisconnected={handleLlmDisconnected} onNavigateToSources={() => setActiveStep(1)} />
        )}
        {step.key === 'connect' && (
          <ConnectSources onSourcesComplete={handleSourcesComplete} agentConnected={llmConnected} />
        )}
        {step.key === 'explorer' && (
          <MappingWizard
            onNavigateToQueue={() => { setActiveStep(4); setPreloadedMapping(null); }}
            preloadedMapping={preloadedMapping}
            onClearPreloaded={() => setPreloadedMapping(null)}
            devMode={devMode}
          />
        )}
        {step.key === 'manuals' && <ManualBuilder preset={manualPreset} onPresetConsumed={() => setManualPreset(null)} />}
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
            onCreateManual={(entityType, identifiers) => {
              setManualPreset({ entityType, identifiers });
              setActiveStep(3);
            }}
          />
        )}
      </div>
    </div>
  );
}
