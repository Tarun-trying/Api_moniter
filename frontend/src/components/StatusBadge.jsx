export default function StatusBadge({ status, size = 'md' }) {
  const s = (status || 'unknown').toLowerCase();
  const labels = {
    up:       'UP',
    down:     'DOWN',
    degraded: 'DEGRADED',
    checking: 'CHECKING',
    unknown:  'UNKNOWN',
  };

  return (
    <span className={`status-badge ${s}`} role="status" aria-label={`Status: ${labels[s] || s}`}>
      <span className="status-dot" aria-hidden="true" />
      {labels[s] || s.toUpperCase()}
    </span>
  );
}
