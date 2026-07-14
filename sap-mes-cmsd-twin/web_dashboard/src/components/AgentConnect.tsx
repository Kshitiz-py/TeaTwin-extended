import { useState, useEffect, useCallback } from 'react';
import { agentApi, AgentStatus, ProviderInfo } from '../services/agentApi';

interface AgentConnectProps {
  onConnected?: () => void;
  onDisconnected?: () => void;
  onNavigateToSources?: () => void;
}

const STORAGE_KEY_PROVIDER = 'agent_connect_provider';
const STORAGE_KEY_TIMEOUT = 'agent_connect_timeout';
const DEFAULT_EMBED_HOST = 'http://host.docker.internal:11434';
const DEFAULT_EMBED_MODEL = 'qwen3-embedding:4b';

// ── Shared styles ──────────────────────────────────────
const C = {
  card: {
    background: '#1e293b', border: '1px solid #334155',
    borderRadius: '10px', padding: '18px',
  } as React.CSSProperties,
  cardTitle: {
    fontSize: '13px', fontWeight: 600, color: '#e2e8f0',
    display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px',
  } as React.CSSProperties,
  row2: {
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px',
  } as React.CSSProperties,
  field: {
    display: 'flex', flexDirection: 'column', gap: '4px',
  } as React.CSSProperties,
  label: {
    fontSize: '10px', fontWeight: 600, color: '#64748b',
    textTransform: 'uppercase' as const, letterSpacing: '0.5px',
  } as React.CSSProperties,
  input: {
    width: '100%', padding: '7px 10px', borderRadius: '6px',
    background: '#0f172a', border: '1px solid #334155', color: '#e2e8f0',
    fontSize: '13px', boxSizing: 'border-box' as const,
    outline: 'none', transition: 'border-color 0.15s',
  } as React.CSSProperties,
  select: {
    width: '100%', padding: '7px 10px', borderRadius: '6px',
    background: '#0f172a', border: '1px solid #334155', color: '#e2e8f0',
    fontSize: '13px', boxSizing: 'border-box' as const, cursor: 'pointer',
    outline: 'none',
  } as React.CSSProperties,
  btn: (kind: 'primary' | 'danger' | 'muted', disabled: boolean) => {
    const base: React.CSSProperties = {
      padding: '8px 18px', borderRadius: '7px', border: 'none',
      cursor: disabled ? 'not-allowed' : 'pointer',
      fontSize: '13px', fontWeight: 600,
      opacity: disabled ? 0.5 : 1,
    };
    if (kind === 'primary') return { ...base, background: '#2563eb', color: '#fff' };
    if (kind === 'danger') return { ...base, background: '#7f1d1d', color: '#fca5a5', border: '1px solid #b91c1c' };
    return { ...base, background: '#334155', color: '#94a3b8', border: '1px solid #475569' };
  },
  pill: (state: 'on' | 'off' | 'unknown') => ({
    padding: '4px 10px', borderRadius: '10px', fontSize: '11px', fontWeight: 600,
    background: state === 'on' ? '#064e3b' : state === 'off' ? '#7f1d1d' : '#1e293b',
    color: state === 'on' ? '#6ee7b7' : state === 'off' ? '#fca5a5' : '#64748b',
    border: state === 'unknown' ? '1px solid #334155' : '1px solid transparent',
    whiteSpace: 'nowrap' as const, lineHeight: '1.4',
  } as React.CSSProperties),
  badge: (apiStyle: string) => {
    const colors: Record<string, string> = { openai: '#10a37f', anthropic: '#d97706', ollama: '#2563eb' };
    return {
      fontSize: '9px', padding: '1px 5px', borderRadius: '3px',
      background: colors[apiStyle] || '#475569', color: '#fff',
      textTransform: 'uppercase' as const, fontWeight: 700, letterSpacing: '0.4px',
    } as React.CSSProperties;
  },
  modelList: {
    maxHeight: '130px', overflowY: 'auto' as const, marginTop: '6px',
    background: '#0f172a', borderRadius: '6px', border: '1px solid #334155',
    padding: '6px', fontSize: '11px', color: '#94a3b8',
  } as React.CSSProperties,
  footnote: {
    fontSize: '10px', color: '#475569', borderTop: '1px solid #1e293b',
    paddingTop: '12px', marginTop: '4px', textAlign: 'center' as const,
  } as React.CSSProperties,
  errorBox: {
    padding: '10px 14px', borderRadius: '7px', background: '#451a1a',
    color: '#fca5a5', fontSize: '12px', fontWeight: 500,
    border: '1px solid #7f1d1d',
  } as React.CSSProperties,
  toggleRow: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '10px 14px', borderRadius: '7px',
    background: '#0f172a', border: '1px solid #334155',
    cursor: 'pointer', userSelect: 'none' as const,
    fontSize: '12px', color: '#e2e8f0', fontWeight: 600,
  } as React.CSSProperties,
};

/** Small button for eye toggle */
function EyeBtn({ show, onClick }: { show: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '6px 10px', borderRadius: '6px', border: '1px solid #334155',
        background: '#0f172a', color: '#94a3b8', cursor: 'pointer', fontSize: '14px',
        flexShrink: 0,
      }}
      tabIndex={-1}
    >
      {show ? '🙈' : '👁'}
    </button>
  );
}

/** Reusable text field with label */
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={C.field}>
      <span style={C.label}>{label}</span>
      {children}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
//  COMPONENT
// ══════════════════════════════════════════════════════════
export default function AgentConnect({ onConnected, onDisconnected, onNavigateToSources }: AgentConnectProps) {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [providersLoading, setProvidersLoading] = useState(true);

  // Chat
  const [chatProvider, setChatProvider] = useState('ollama');
  const [chatHost, setChatHost] = useState('http://localhost:11434');
  const [chatApiKey, setChatApiKey] = useState('');
  const [chatModel, setChatModel] = useState('qwen3.5:397b-cloud');
  const [chatEmbedModel, setChatEmbedModel] = useState('');
  const [chatShowKey, setChatShowKey] = useState(false);

  // Embed
  const [useSeparateEmbed, setUseSeparateEmbed] = useState(true);
  const [embedProvider, setEmbedProvider] = useState('ollama');
  const [embedHost, setEmbedHost] = useState(DEFAULT_EMBED_HOST);
  const [embedApiKey, setEmbedApiKey] = useState('');
  const [embedModel, setEmbedModel] = useState(DEFAULT_EMBED_MODEL);
  const [embedShowKey, setEmbedShowKey] = useState(false);

  // Connection
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [testing, setTesting] = useState(false);
  const [chatHealth, setChatHealth] = useState<boolean | null>(null);
  const [embedHealth, setEmbedHealth] = useState<boolean | null>(null);
  const [testResult, setTestResult] = useState<'connected' | 'failed' | null>(null);

  // Misc
  const [availableModels, setAvailableModels] = useState<{ id: string; name: string }[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [timeoutSec, setTimeoutSec] = useState(() => {
    try { return Number(localStorage.getItem(STORAGE_KEY_TIMEOUT)) || 15; } catch { return 15; }
  });

  // ── Init ──────────────────────────────────────────────
  const fetchProviders = useCallback(async () => {
    setProvidersLoading(true);
    try {
      const data = await agentApi.listProviders();
      setProviders(data.providers || []);
      let sel = '';
      try { sel = localStorage.getItem(STORAGE_KEY_PROVIDER) || ''; } catch { /* */ }
      const matched = sel && data.providers?.find((p: ProviderInfo) => p.name === sel);
      if (data.providers?.length) {
        const first = matched || data.providers[0];
        setChatProvider(first.name);
        setChatHost(first.host);
        setChatModel(first.chat_model);
        setChatEmbedModel(first.embed_model);
      }
    } catch { setProviders([]); } finally { setProvidersLoading(false); }
  }, []);

  const checkStatus = async () => {
    try {
      const s = await agentApi.getAgentStatus();
      setStatus(s);
      setChatHealth(s.connected);
      if (s.host) setChatHost(s.host);
      if (s.chat_model) setChatModel(s.chat_model);
      if (s.embed_model) setChatEmbedModel(s.embed_model);
      if (s.provider_type) setChatProvider(s.provider_type);
      // Restore embed state from backend — it persists in ProviderManager memory
      if (s.embed_provider && typeof s.embed_provider === 'object') {
        setUseSeparateEmbed(true);
        setEmbedProvider(s.embed_provider.provider_type);
        setEmbedHost(s.embed_provider.host);
        setEmbedModel(s.embed_provider.embed_model);
        setEmbedHealth(true);
      }
    } catch { setStatus(null); setChatHealth(false); }
  };

  useEffect(() => { fetchProviders(); checkStatus(); }, [fetchProviders]);

  const fetchModels = useCallback(async () => {
    setLoadingModels(true);
    try { const r = await agentApi.listModels(); setAvailableModels(r.models || []); }
    catch { setAvailableModels([]); }
    finally { setLoadingModels(false); }
  }, []);

  // ── Helpers ───────────────────────────────────────────
  const getInfo = (name: string) => providers.find(p => p.name === name);
  const persistProvider = (name: string) => { try { localStorage.setItem(STORAGE_KEY_PROVIDER, name); } catch { /* */ } };
  const persistTimeout = (t: number) => { try { localStorage.setItem(STORAGE_KEY_TIMEOUT, String(t)); } catch { /* */ } };

  const activeChatInfo = getInfo(chatProvider);
  const activeEmbedInfo = useSeparateEmbed ? getInfo(embedProvider) : null;

  const handleChatProviderChange = (name: string) => {
    setChatProvider(name); persistProvider(name);
    const info = getInfo(name);
    if (info) {
      setChatHost(info.host);
      setChatModel(info.chat_model);
      setChatEmbedModel(info.embed_model);
    }
  };

  const handleEmbedProviderChange = (name: string) => {
    setEmbedProvider(name);
    const info = getInfo(name);
    if (info) {
      setEmbedHost(info.host);
      setEmbedModel(name === 'ollama' ? DEFAULT_EMBED_MODEL : info.embed_model);
    }
  };

  // ── Connect / Disconnect Agent ─────────────────────────
  const connectAgent = async () => {
    setTesting(true); setTestResult(null); setChatHealth(null);
    try {
      const result = await agentApi.connectAgent({
        chat: { provider_type: chatProvider, host: chatHost, api_key: chatApiKey, chat_model: chatModel, embed_model: useSeparateEmbed ? '' : chatEmbedModel },
      }, timeoutSec);
      const ok = result.connection_test?.chat?.ok ?? false;
      setChatHealth(ok);
      if (ok) {
        setStatus({ connected: true, host: chatHost, chat_model: chatModel, embed_model: chatEmbedModel, has_api_key: !!chatApiKey, provider_type: chatProvider });
        setTestResult('connected');
      } else { setTestResult('failed'); }
    } catch { setTestResult('failed'); setChatHealth(false); }
    setTesting(false);
  };

  const disconnectAgent = async () => {
    setTesting(true);
    try { await agentApi.disconnectAgent(); } catch { /* */ }
    setChatHealth(null); setEmbedHealth(null);
    setStatus(prev => prev ? { ...prev, connected: false } : null);
    setTesting(false);
    onDisconnected?.();
  };

  // ── Connect / Disconnect Embed ─────────────────────────
  const connectEmbed = async () => {
    setTesting(true); setEmbedHealth(null);
    try {
      const result = await agentApi.connectAgent({
        chat: { provider_type: chatProvider, host: chatHost, api_key: chatApiKey, chat_model: chatModel, embed_model: '' },
        embed: { provider_type: embedProvider, host: embedHost, api_key: embedApiKey, chat_model: '', embed_model: embedModel },
      }, timeoutSec);
      const ok = result.connection_test?.embed?.ok ?? false;
      setEmbedHealth(ok);
      if (ok) {
        setStatus(prev => prev ? { ...prev, embed_model: embedModel, embed_provider: { provider_type: embedProvider, host: embedHost, chat_model: '', embed_model: embedModel, has_api_key: !!embedApiKey } } : prev);
      }
    } catch { setEmbedHealth(false); }
    setTesting(false);
  };

  const disconnectEmbed = async () => {
    setTesting(true);
    try { await agentApi.disconnectAgent(); } catch { /* */ }
    setEmbedHealth(null);
    setTesting(false);
  };

  // ── Status helpers ─────────────────────────────────────
  const agentState: 'on' | 'off' | 'unknown' = chatHealth === true ? 'on' : chatHealth === false ? 'off' : 'unknown';
  const embedState: 'on' | 'off' | 'unknown' = embedHealth === true ? 'on' : 'off';

  // ══════════════════════════════════════════════════════
  //  RENDER
  // ══════════════════════════════════════════════════════
  return (
    <div style={{ maxWidth: 620, margin: '16px auto', display: 'flex', flexDirection: 'column', gap: '14px' }}>

      {/* ── HEADER ──────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f1f5f9', margin: 0 }}>AI Agent Connection</h3>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={C.pill(agentState)}>
            {agentState === 'on' ? '● Agent Online' : agentState === 'off' ? '● Agent Offline' : '○ Agent —'}
          </span>
          <span style={C.pill(useSeparateEmbed ? embedState : agentState)}>
            {useSeparateEmbed
              ? (embedState === 'on' ? '● Embed Online' : embedState === 'off' ? '● Embed Offline' : '○ Embed —')
              : (agentState === 'on' ? '● Embed Online' : agentState === 'off' ? '● Embed Offline' : '○ Embed —')}
          </span>
        </div>
      </div>

      {/* ── CARD 1 : CHAT AGENT ──────────────────────── */}
      <div style={C.card}>
        <div style={C.cardTitle}>
          💬 Chat Agent
          {activeChatInfo && <span style={C.badge(activeChatInfo.api_style)}>{activeChatInfo.api_style}</span>}
        </div>

        {/* Row 1: Provider + Host */}
        <div style={{ ...C.row2, marginBottom: '10px' }}>
          <Field label="Provider">
            {providersLoading ? (
              <div style={{ ...C.input, color: '#64748b' }}>Loading…</div>
            ) : (
              <select value={chatProvider} onChange={e => handleChatProviderChange(e.target.value)} style={C.select}>
                {providers.map(p => (
                  <option key={p.name} value={p.name}>{p.label} {p.requires_api_key ? '🔑' : ''}</option>
                ))}
              </select>
            )}
          </Field>
          <Field label="Host URL">
            <input value={chatHost} onChange={e => setChatHost(e.target.value)} placeholder="https://api.example.com" style={C.input} />
          </Field>
        </div>

        {/* Row 2: API Key */}
        <div style={{ marginBottom: '10px' }}>
          <Field label={`API Key ${status?.has_api_key ? '(key set)' : ''}`}>
            <div style={{ display: 'flex', gap: '6px' }}>
              <input
                type={chatShowKey ? 'text' : 'password'}
                value={chatApiKey}
                onChange={e => setChatApiKey(e.target.value)}
                placeholder={status?.has_api_key ? '•••••••• (leave empty)' : 'sk-…'}
                style={{ ...C.input, flex: 1 }}
              />
              <EyeBtn show={chatShowKey} onClick={() => setChatShowKey(!chatShowKey)} />
            </div>
          </Field>
        </div>

        {/* Row 3: Model(s) */}
        <div style={{ ...C.row2, marginBottom: '10px' }}>
          <Field label="Chat Model">
            <input value={chatModel} onChange={e => setChatModel(e.target.value)} style={C.input} />
          </Field>
          {!useSeparateEmbed ? (
            <Field label="Embed Model">
              <input value={chatEmbedModel} onChange={e => setChatEmbedModel(e.target.value)} placeholder="(none)" style={C.input} />
            </Field>
          ) : (
            <Field label="Timeout (seconds)">
              <input
                type="number" min={3} max={120} value={timeoutSec}
                onChange={e => { const v = Number(e.target.value); setTimeoutSec(v); persistTimeout(v); }}
                style={{ ...C.input, width: '80px' }}
              />
            </Field>
          )}
        </div>

        {/* Fetch models */}
        <div style={{ marginBottom: '14px' }}>
          <button
            onClick={fetchModels}
            disabled={loadingModels || chatHealth !== true}
            style={C.btn('muted', loadingModels || chatHealth !== true)}
          >
            {loadingModels ? '⏳ Fetching…' : '📋 Fetch Available Models'}
          </button>
          {availableModels.length > 0 && (
            <div style={C.modelList}>
              {availableModels.map(m => (
                <div key={m.id} onClick={() => setChatModel(m.id)}
                  style={{
                    padding: '3px 8px', cursor: 'pointer', borderRadius: '4px',
                    background: chatModel === m.id ? '#1e3a5f' : 'transparent',
                    color: chatModel === m.id ? '#93c5fd' : '#94a3b8',
                  }}
                >{m.name}</div>
              ))}
            </div>
          )}
        </div>

        {/* Action row */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          {chatHealth === true ? (
            <button onClick={disconnectAgent} disabled={testing} style={C.btn('danger', testing)}>
              {testing ? '...' : '🔌 Disconnect Agent'}
            </button>
          ) : (
            <button onClick={connectAgent} disabled={testing || !chatHost || providersLoading} style={C.btn('primary', testing || !chatHost || providersLoading)}>
              {testing ? '...' : '🤖 Connect Agent'}
            </button>
          )}
          {useSeparateEmbed && chatHealth !== true && (
            <span style={{ fontSize: '11px', color: '#64748b' }}>
              Timeout: {timeoutSec}s
            </span>
          )}
        </div>
      </div>

      {/* ── CARD 2 : EMBEDDING PROVIDER ────────────────── */}
      <div style={C.card}>
        <div
          style={C.toggleRow}
          onClick={() => setUseSeparateEmbed(!useSeparateEmbed)}
        >
          <span>🧬 Separate Embedding Provider</span>
          <span style={{
            width: '36px', height: '20px', borderRadius: '10px',
            background: useSeparateEmbed ? '#2563eb' : '#334155',
            display: 'flex', alignItems: 'center', padding: '2px',
            transition: 'background 0.2s',
          }}>
            <span style={{
              width: '16px', height: '16px', borderRadius: '50%',
              background: '#fff',
              transform: useSeparateEmbed ? 'translateX(16px)' : 'translateX(0)',
              transition: 'transform 0.2s',
            }} />
          </span>
        </div>

        {useSeparateEmbed && (
          <div style={{ marginTop: '14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {/* Row 1: Provider + Host */}
            <div style={C.row2}>
              <Field label="Provider">
                <select value={embedProvider} onChange={e => handleEmbedProviderChange(e.target.value)} style={C.select}>
                  {providers.filter(p => p.has_embeddings || p.name === 'custom').map(p => (
                    <option key={p.name} value={p.name}>{p.label} 🧬</option>
                  ))}
                </select>
              </Field>
              <Field label="Host URL">
                <input value={embedHost} onChange={e => setEmbedHost(e.target.value)} placeholder={DEFAULT_EMBED_HOST} style={C.input} />
              </Field>
            </div>

            {/* Row 2: API Key */}
            <Field label="API Key">
              <div style={{ display: 'flex', gap: '6px' }}>
                <input
                  type={embedShowKey ? 'text' : 'password'}
                  value={embedApiKey}
                  onChange={e => setEmbedApiKey(e.target.value)}
                  placeholder="(optional)"
                  style={{ ...C.input, flex: 1 }}
                />
                <EyeBtn show={embedShowKey} onClick={() => setEmbedShowKey(!embedShowKey)} />
              </div>
            </Field>

            {/* Row 3: Model + Timeout */}
            <div style={C.row2}>
              <Field label="Embedding Model">
                <input value={embedModel} onChange={e => setEmbedModel(e.target.value)} placeholder={DEFAULT_EMBED_MODEL} style={C.input} />
              </Field>
              <Field label="Timeout (seconds)">
                <input
                  type="number" min={3} max={120} value={timeoutSec}
                  onChange={e => { const v = Number(e.target.value); setTimeoutSec(v); persistTimeout(v); }}
                  style={{ ...C.input, width: '80px' }}
                />
              </Field>
            </div>

            {/* Action */}
            <div style={{ marginTop: '4px' }}>
              {embedHealth === true ? (
                <button onClick={disconnectEmbed} disabled={testing} style={C.btn('danger', testing)}>
                  {testing ? '...' : '🔌 Disconnect Embed'}
                </button>
              ) : (
                <button onClick={connectEmbed} disabled={testing || !embedHost} style={{
                  ...C.btn('primary', testing || !embedHost),
                  background: testing || !embedHost ? '#334155' : '#4f46e5',
                }}>
                  {testing ? '...' : '🧬 Connect Embed'}
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── NAVIGATION ────────────────────────────────── */}
      {onNavigateToSources && (
        (() => {
          const ready = useSeparateEmbed ? (chatHealth === true && embedHealth === true) : (chatHealth === true);
          return (
            <button
              onClick={ready ? onNavigateToSources : undefined}
              disabled={!ready}
              style={{
                width: '100%', padding: '10px 18px', borderRadius: '8px', border: 'none',
                cursor: ready ? 'pointer' : 'not-allowed',
                fontSize: '13px', fontWeight: 600,
                background: ready ? '#166534' : '#1e293b',
                color: ready ? '#4ade80' : '#475569',
                border: ready ? '1px solid #166534' : '1px solid #334155',
              }}
            >
              → Connect Sources
            </button>
          );
        })()
      )}

      {/* ── ERROR ─────────────────────────────────────── */}
      {testResult === 'failed' && (
        <div style={C.errorBox}>
          ❌ Connection failed — check host URL and API key
        </div>
      )}

      {/* ── FOOTER ────────────────────────────────────── */}
      <div style={C.footnote}>
        🔒 API keys held in memory only — never written to disk or logs. Cleared on restart.
      </div>
    </div>
  );
}