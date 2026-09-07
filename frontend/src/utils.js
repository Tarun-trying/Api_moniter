// Shared utility: format relative time like "20 seconds ago"
export function timeAgo(dateStr) {
  if (!dateStr) return '—';
  const date = new Date(dateStr + (dateStr.endsWith('Z') ? '' : 'Z'));
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diff < 5)   return 'just now';
  if (diff < 60)  return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function formatDuration(startStr, endStr) {
  if (!startStr) return '—';
  const start = new Date(startStr + (startStr.endsWith('Z') ? '' : 'Z'));
  const end   = endStr ? new Date(endStr + (endStr.endsWith('Z') ? '' : 'Z')) : new Date();
  const secs  = Math.floor((end - start) / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins} minute${mins !== 1 ? 's' : ''}`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ${mins % 60}m`;
}

export function formatDateTime(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr + (dateStr.endsWith('Z') ? '' : 'Z'));
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function formatResponseTime(ms) {
  if (ms == null) return '—';
  return `${Math.round(ms)} ms`;
}

export function formatUptime(pct) {
  if (pct == null) return '—';
  return `${pct.toFixed(2)}%`;
}
