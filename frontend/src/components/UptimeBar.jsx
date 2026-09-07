/**
 * Renders a horizontal bar of colored segments representing check history.
 * segments: [{success, status_code, checked_at, response_time}]
 */
export default function UptimeBar({ segments = [], maxSegments = 80 }) {
  // If no data, show empty segments
  if (segments.length === 0) {
    return (
      <div className="uptime-bar" aria-label="No uptime data">
        {Array.from({ length: maxSegments }).map((_, i) => (
          <div key={i} className="uptime-segment empty" />
        ))}
      </div>
    );
  }

  // Subsample if too many
  const step = Math.ceil(segments.length / maxSegments);
  const sampled = [];
  for (let i = 0; i < segments.length; i += step) {
    sampled.push(segments[i]);
  }

  return (
    <div className="uptime-bar" role="img" aria-label="Uptime history bar">
      {sampled.map((seg, i) => {
        const cls = seg.success ? 'success' : 'failure';
        const label = seg.success
          ? `OK ${seg.checked_at?.slice(0, 16) || ''}`
          : `Failed ${seg.checked_at?.slice(0, 16) || ''}`;
        return (
          <div
            key={i}
            className={`uptime-segment ${cls} tooltip-wrapper`}
            role="presentation"
          >
            <span className="tooltip-content">{label}</span>
          </div>
        );
      })}
    </div>
  );
}
