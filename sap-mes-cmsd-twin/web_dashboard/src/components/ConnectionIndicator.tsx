import { ConnectionMetadata } from '../services/api';

interface ConnectionIndicatorProps {
  entity: any;
  showLabel?: boolean;
}

export default function ConnectionIndicator({ entity, showLabel = true }: ConnectionIndicatorProps) {
  const conn: ConnectionMetadata | undefined = entity?._connection;

  if (!conn) {
    return (
      <span
        title="Static data — no API connection"
        style={{ color: '#64748b', fontSize: '10px', cursor: 'help' }}
      >
        ○ {showLabel && 'Static'}
      </span>
    );
  }

  const ageMinutes = conn.last_fetched
    ? Math.round((Date.now() - new Date(conn.last_fetched).getTime()) / 60000)
    : null;

  const isStale = ageMinutes !== null && ageMinutes > 5;
  const sourceLabel = conn.source_url?.split('/').pop() || conn.source_url || 'API';

  return (
    <span
      title={[
        `Source: ${conn.source_url}`,
        `Key: ${conn.key_field} = ${conn.key_value}`,
        `Mapping: ${conn.mapping_id}`,
        ageMinutes !== null ? `Last fetched: ${ageMinutes}m ago` : '',
      ].join('\n')}
      style={{
        color: isStale ? '#f59e0b' : '#22c55e',
        fontSize: '10px',
        cursor: 'help',
      }}
    >
      {isStale ? '◌' : '●'} {showLabel && sourceLabel}
      {ageMinutes !== null && ` · ${ageMinutes}m`}
    </span>
  );
}
