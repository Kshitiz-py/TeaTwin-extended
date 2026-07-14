import { useState, useEffect, useRef, useCallback } from 'react';

interface ChangeEvent {
  entity_type: string;
  entity_identifier: string;
  entity_name: string;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  event_type: string;
  timestamp: string;
}

interface UseWebSocketResult {
  events: ChangeEvent[];
  connected: boolean;
  clearEvents: () => void;
}

export function useWebSocket(): UseWebSocketResult {
  const [events, setEvents] = useState<ChangeEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/cmsd/v1/ws/events`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (msg) => {
      try {
        const event: ChangeEvent = JSON.parse(msg.data);
        if (event.event_type !== 'connected') {
          setEvents(prev => {
            const updated = [event, ...prev];
            return updated.slice(0, 200); // cap at 200
          });
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setConnected(false);
      reconnectRef.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  const clearEvents = useCallback(() => setEvents([]), []);

  return { events, connected, clearEvents };
}