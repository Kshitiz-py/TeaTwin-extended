import { useEffect, useState } from 'react';
import { api } from '../services/api';

interface Order {
  identifier: string;
  status: string;
  due_date: string | null;
  line_count: number;
}

const statusColor = (s: string): string => {
  switch (s) {
    case 'created': return '#94a3b8';
    case 'released': return '#3b82f6';
    case 'completed': return '#22c55e';
    case 'shipped': return '#a855f7';
    case 'cancelled': return '#ef4444';
    default: return '#64748b';
  }
};

export default function OrderTracker() {
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    api.getOrders().then(setOrders).catch(() => {});
    const interval = setInterval(() => {
      api.getOrders().then(setOrders).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h3 style={{ color: '#f1f5f9', marginBottom: '16px' }}>Production Orders ({orders.length})</h3>
      <div style={{ display: 'grid', gap: '8px' }}>
        {orders.map(o => (
          <div key={o.identifier} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: '#1e293b', borderRadius: '8px', padding: '14px 16px',
            border: '1px solid #334155',
          }}>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: '14px', fontWeight: 600, color: '#f1f5f9' }}>{o.identifier}</p>
              <p style={{ fontSize: '11px', color: '#64748b' }}>Due: {o.due_date ? new Date(o.due_date).toLocaleDateString() : 'N/A'} · {o.line_count} lines</p>
            </div>
            <span style={{
              padding: '4px 14px', borderRadius: '12px', fontSize: '11px', fontWeight: 600,
              background: statusColor(o.status) + '20', color: statusColor(o.status),
              border: `1px solid ${statusColor(o.status)}40`,
            }}>
              {o.status}
            </span>
          </div>
        ))}
      </div>
      {orders.length === 0 && <p style={{ color: '#64748b', textAlign: 'center', marginTop: '40px' }}>No orders loaded</p>}
    </div>
  );
}