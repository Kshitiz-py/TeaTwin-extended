import { useState, useRef, useEffect } from 'react';

interface ChatMessage {
  role: 'user' | 'agent';
  content: string;
  timestamp: string;
  mappingSuggestion?: any;
}

interface MappingChatProps {
  dataPointName: string;
  currentMapping: any;
  onSendMessage: (message: string) => Promise<string>;
  onApplyMappingUpdate?: (updatedMapping: any) => void;
  isOpen: boolean;
  onToggle: () => void;
}

function extractMappingSuggestion(
  userQuestion: string,
  aiResponse: string,
  currentMapping: any
): any | null {
  const lowerQ = userQuestion.toLowerCase();
  const lowerR = aiResponse.toLowerCase();

  // Detect if the response contains mapping guidance
  const guidanceKeywords = [
    'should come from',
    'should map to',
    'instead of',
    'change the mapping',
    'api path:',
    'type conversion:',
    'use',
    'replace',
  ];

  const hasGuidance = guidanceKeywords.some(kw => lowerR.includes(kw));
  if (!hasGuidance) return null;

  // Try to find CMSD field names in the question
  const cmsdFields = [
    'identifier', 'name', 'description', 'resource_type', 'capacity',
    'availability', 'mttr', 'mtbf', 'mcbf', 'reliability',
    'cycle_time', 'size', 'weight', 'decision_rule', 'routing_rule',
    'transport_capacity', 'worker_count', 'current_status',
    'production_status', 'status', 'due_date', 'release_date',
    'priority', 'start_time', 'planned_effort', 'quantity',
    'production_days_per_year', 'connection_type',
    'from_resource_id', 'to_resource_id',
  ];

  const mentionedFields = cmsdFields.filter(f => lowerQ.includes(f));

  // Try to find API path suggestions in the response
  const apiPathMatch = aiResponse.match(/api_path["\s:]+([^\s",}]+)/i)
    || aiResponse.match(/from\s+["']?([/\w-]+)["']?\s*(api|endpoint)/i);

  const conversionMatch = aiResponse.match(/(?:use|apply)\s+(to_\w+|none)/i)
    || aiResponse.match(/type_conversion["\s:]+(to_\w+|none)/i);

  if (mentionedFields.length === 0 && !apiPathMatch) return null;

  const suggestion: any = {};
  const mapping = currentMapping?.mapping || currentMapping || {};

  for (const field of mentionedFields) {
    const updated: any = { confidence: 'manual' };
    if (apiPathMatch) updated.api_path = apiPathMatch[1];
    if (conversionMatch) updated.type_conversion = conversionMatch[1];
    if (Object.keys(updated).length > 1) {
      suggestion[field] = updated;
    }
  }

  return Object.keys(suggestion).length > 0 ? { mapping: suggestion } : null;
}

export default function MappingChat({
  dataPointName,
  currentMapping,
  onSendMessage,
  onApplyMappingUpdate,
  isOpen,
  onToggle,
}: MappingChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [appliedMsgs, setAppliedMsgs] = useState<Set<number>>(new Set());
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input;
    const msg: ChatMessage = { role: 'user', content: userMsg, timestamp: new Date().toLocaleTimeString() };
    setMessages(prev => [...prev, msg]);
    setInput('');
    setLoading(true);
    try {
      const resp = await onSendMessage(userMsg);
      const suggestion = extractMappingSuggestion(userMsg, resp, currentMapping);
      setMessages(prev => [
        ...prev,
        {
          role: 'agent',
          content: resp,
          timestamp: new Date().toLocaleTimeString(),
          mappingSuggestion: suggestion,
        },
      ]);
    } catch {
      setMessages(prev => [
        ...prev,
        {
          role: 'agent',
          content: 'Sorry, something went wrong.',
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
    }
    setLoading(false);
  };

  const applySuggestion = (index: number, suggestion: any) => {
    if (onApplyMappingUpdate && suggestion) {
      // Extract mapping fields from the suggestion and apply them
      const mappingFields = suggestion.mapping || {};
      const updatedMapping: any = {
        ...currentMapping,
        mapping: { ...(currentMapping?.mapping || currentMapping || {}) },
      };
      for (const [field, updates] of Object.entries(mappingFields) as [string, any][]) {
        updatedMapping.mapping[field] = {
          ...(updatedMapping.mapping[field] || {}),
          ...updates,
        };
      }
      onApplyMappingUpdate(updatedMapping);
      setAppliedMsgs(prev => new Set(prev).add(index));
    }
  };

  const handleKey = (e: any) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <>
      <button
        onClick={onToggle}
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          zIndex: 100,
          padding: '10px 18px',
          background: '#3b82f6',
          color: '#fff',
          border: 'none',
          borderRadius: '24px',
          cursor: 'pointer',
          fontSize: '14px',
          fontWeight: 600,
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}
      >
        💬 Chat with Agent
        {messages.length > 0 && (
          <span
            style={{
              background: '#ef4444',
              color: '#fff',
              borderRadius: '10px',
              padding: '1px 7px',
              fontSize: '10px',
              fontWeight: 700,
            }}
          >
            {messages.length}
          </span>
        )}
      </button>
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            right: 0,
            width: '380px',
            height: '100vh',
            background: '#0f172a',
            borderLeft: '1px solid #334155',
            zIndex: 200,
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '-4px 0 20px rgba(0,0,0,0.3)',
          }}
        >
          <div
            style={{
              padding: '12px 16px',
              background: '#1e293b',
              borderBottom: '1px solid #334155',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <p style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#f1f5f9' }}>
                Mapping Chat
              </p>
              <p style={{ margin: 0, fontSize: '11px', color: '#94a3b8' }}>{dataPointName}</p>
            </div>
            <button
              onClick={onToggle}
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                fontSize: '18px',
              }}
            >
              ×
            </button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
            {messages.length === 0 && (
              <div style={{ padding: '24px 12px', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
                <p style={{ margin: '0 0 8px', fontSize: '20px' }}>🤖</p>
                <p style={{ margin: 0, lineHeight: '1.5' }}>
                  Ask questions about this mapping or give guidance for reanalysis.
                </p>
                <p style={{ margin: '8px 0 0', fontSize: '11px', color: '#475569' }}>
                  e.g., "MTTR should come from /incidents API"
                </p>
              </div>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                style={{
                  marginBottom: '10px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: m.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    maxWidth: '90%',
                    padding: '8px 12px',
                    borderRadius: '12px',
                    background: m.role === 'user' ? '#1e293b' : '#334155',
                    color: '#f1f5f9',
                    fontSize: '13px',
                    lineHeight: '1.4',
                    border: m.role === 'agent' ? '1px solid #475569' : 'none',
                  }}
                >
                  <span style={{ fontSize: '11px', opacity: 0.7, marginRight: '4px' }}>
                    {m.role === 'user' ? '👤' : '🤖'}
                  </span>
                  {m.content}

                  {m.role === 'agent' && m.mappingSuggestion && onApplyMappingUpdate && (
                    <div
                      style={{
                        marginTop: '8px',
                        paddingTop: '8px',
                        borderTop: '1px solid #475569',
                      }}
                    >
                      {appliedMsgs.has(i) ? (
                        <span
                          style={{
                            fontSize: '11px',
                            color: '#4ade80',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          ✅ Applied to mapping
                        </span>
                      ) : (
                        <button
                          onClick={() => applySuggestion(i, m.mappingSuggestion)}
                          style={{
                            padding: '5px 12px',
                            borderRadius: '4px',
                            border: '1px solid #7c3aed',
                            background: 'rgba(124,58,237,0.15)',
                            color: '#a78bfa',
                            cursor: 'pointer',
                            fontSize: '11px',
                            fontWeight: 500,
                          }}
                        >
                          🎯 Apply to Mapping
                        </button>
                      )}
                    </div>
                  )}
                </div>
                <span style={{ fontSize: '10px', color: '#64748b', marginTop: '2px' }}>
                  {m.timestamp}
                </span>
              </div>
            ))}
            {loading && (
              <div style={{ color: '#94a3b8', fontSize: '13px', fontStyle: 'italic' }}>
                🤖 Thinking...
              </div>
            )}
            <div ref={endRef} />
          </div>
          <div
            style={{
              padding: '10px',
              borderTop: '1px solid #334155',
              display: 'flex',
              gap: '6px',
            }}
          >
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask about this mapping..."
              disabled={loading}
              style={{
                flex: 1,
                background: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '6px',
                padding: '8px 10px',
                color: '#f1f5f9',
                fontSize: '13px',
              }}
            />
            <button
              onClick={send}
              disabled={loading}
              style={{
                padding: '8px 14px',
                background: '#3b82f6',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '13px',
                fontWeight: 500,
              }}
            >
              Send
            </button>
          </div>
        </div>
      )}
    </>
  );
}