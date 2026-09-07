import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';

import { monitors as monitorsApi, checks as checksApi } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import UptimeBar from '../components/UptimeBar';
import { timeAgo, formatResponseTime, formatUptime, formatDateTime } from '../utils';

const TIME_RANGES = [
  { label: '24H', hours: 24 },
  { label: '7D',  hours: 168 },
  { label: '30D', hours: 720 },
];

function CheckRow({ check }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <>
      <tr
        onClick={() => setExpanded(e => !e)}
        style={{ cursor: 'pointer' }}
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && setExpanded(x => !x)}
        aria-expanded={expanded}
      >
        <td style={{ fontSize: '12px', color: 'var(--color-muted)' }}>
          {formatDateTime(check.checked_at)}
        </td>
        <td>
          <span className={`check-status-icon ${check.success ? 'success' : 'failure'}`}>
            {check.success ? (
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            ) : (
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            )}
            {check.success ? 'Success' : 'Failed'}
          </span>
        </td>
        <td className="td-mono">{formatResponseTime(check.response_time)}</td>
        <td className="td-mono" style={{ color: 'var(--color-muted)' }}>
          {check.status_code || '—'}
        </td>
        <td>
          {check.content_check_passed !== null && check.content_check_passed !== undefined && (
            <span style={{ fontSize: '12px', color: check.content_check_passed ? 'var(--color-up)' : 'var(--color-down)' }}>
              {check.content_check_passed ? '✓ Content OK' : '✕ Content failed'}
            </span>
          )}
        </td>
      </tr>
      {expanded && check.error_message && (
        <tr style={{ background: 'var(--color-down-bg)' }}>
          <td colSpan={5} style={{ padding: '10px 16px', fontSize: '12.5px', color: 'var(--color-down)' }}>
            <strong>Error:</strong> {check.error_message}
          </td>
        </tr>
      )}
    </>
  );
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      padding: '8px 12px',
      fontSize: '12.5px',
    }}>
      <p style={{ color: 'var(--color-muted)', marginBottom: 4 }}>
        {new Date(label + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </p>
      <p style={{ fontWeight: 600, color: 'var(--color-accent)' }}>
        {payload[0].value != null ? `${Math.round(payload[0].value)} ms` : '—'}
      </p>
    </div>
  );
}

export default function MonitorDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [monitor, setMonitor]   = useState(null);
  const [checks,  setChecks]    = useState([]);
  const [uptime,  setUptime]    = useState(null);
  const [segments, setSegments] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [incidents, setIncidents] = useState([]);

  const [timeRange, setTimeRange] = useState(24);
  const [loading,  setLoading]   = useState(true);
  const [error,    setError]     = useState('');
  const [checking, setChecking]  = useState(false);

  const load = useCallback(async () => {
    try {
      setError('');
      const [mon, chk, upt, seg, chart, inc] = await Promise.all([
        monitorsApi.get(id),
        checksApi.list(id, 50),
        checksApi.uptime(id),
        checksApi.segments(id, timeRange),
        checksApi.chart(id, timeRange),
        fetch(`/api/monitors/${id}/incidents`).then(r => r.json()),
      ]);
      setMonitor(mon);
      setChecks(chk);
      setUptime(upt);
      setSegments(seg);
      setChartData(chart);
      setIncidents(Array.isArray(inc) ? inc : []);
    } catch (err) {
      setError('Failed to load monitor data.');
    } finally {
      setLoading(false);
    }
  }, [id, timeRange]);

  useEffect(() => { load(); }, [load]);

  const handleCheckNow = async () => {
    setChecking(true);
    try {
      await monitorsApi.check(id);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setChecking(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete monitor "${monitor?.name}"? This cannot be undone.`)) return;
    try {
      await monitorsApi.delete(id);
      navigate('/');
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <div className="page">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[280, 160, 80, 240, 200].map((w, i) => (
            <span key={i} className="skeleton" style={{ width: w, height: i === 0 ? 24 : 16 }} />
          ))}
        </div>
      </div>
    );
  }

  if (!monitor) {
    return (
      <div className="page">
        <div className="empty-state">
          <p className="empty-state-title">Monitor not found.</p>
          <button className="btn btn-secondary" onClick={() => navigate('/')}>Back to Dashboard</button>
        </div>
      </div>
    );
  }

  const uptimeFor = (key) => uptime?.[key] != null ? formatUptime(uptime[key]) : '—';

  return (
    <div className="page">
      {/* ── Back ──────────────────────────────────────────────────────── */}
      <button className="back-link" onClick={() => navigate('/')} aria-label="Back to monitors">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M19 12H5M12 5l-7 7 7 7"/>
        </svg>
        Monitors
      </button>

      {error && (
        <div className="error-banner" role="alert">{error}</div>
      )}

      {/* ── Header ───────────────────────────────────────────────────── */}
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <h1 className="page-title" style={{ marginBottom: 0 }}>{monitor.name}</h1>
            <StatusBadge status={monitor.last_status || 'checking'} />
          </div>
          <p className="page-subtitle" style={{ fontFamily: 'monospace', fontSize: '12.5px' }}>{monitor.url}</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            className="btn btn-secondary"
            onClick={handleCheckNow}
            disabled={checking}
            id="check-now-btn"
          >
            {checking
              ? <><span className="spinner" /> Checking…</>
              : <>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4.5"/>
                  </svg>
                  Check Now
                </>
            }
          </button>
          <button className="btn btn-danger btn-sm" onClick={handleDelete} id="delete-monitor-btn">
            Delete
          </button>
        </div>
      </div>

      {/* ── Metrics Grid ─────────────────────────────────────────────── */}
      <div className="metric-grid" role="region" aria-label="Monitor metrics">
        <div className="metric-item">
          <div className="metric-label">Response Time</div>
          <div className="metric-value mono">{formatResponseTime(monitor.last_response_time)}</div>
        </div>
        <div className="metric-item">
          <div className="metric-label">HTTP Status</div>
          <div className="metric-value mono">{monitor.last_status_code || '—'}</div>
        </div>
        <div className="metric-item">
          <div className="metric-label">Uptime (24h)</div>
          <div className="metric-value">{uptimeFor('uptime_24h')}</div>
        </div>
        <div className="metric-item">
          <div className="metric-label">Last Checked</div>
          <div className="metric-value" style={{ fontSize: '14px' }}>{timeAgo(monitor.last_checked_at)}</div>
        </div>
        <div className="metric-item">
          <div className="metric-label">Interval</div>
          <div className="metric-value" style={{ fontSize: '14px' }}>
            {monitor.interval >= 3600
              ? `${monitor.interval / 3600}h`
              : monitor.interval >= 60
              ? `${monitor.interval / 60}m`
              : `${monitor.interval}s`}
          </div>
        </div>
      </div>

      {/* ── Response Time Chart ───────────────────────────────────────── */}
      <div className="chart-card">
        <div className="chart-header">
          <h2 className="chart-title">Response Time</h2>
          <div className="time-filters" role="group" aria-label="Time range">
            {TIME_RANGES.map(r => (
              <button
                key={r.hours}
                className={`time-filter-btn${timeRange === r.hours ? ' active' : ''}`}
                onClick={() => setTimeRange(r.hours)}
                aria-pressed={timeRange === r.hours}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        {chartData.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--color-muted)', fontSize: '13px' }}>
            No data for this period.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="rtGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#2563eb" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="time"
                tickFormatter={v => {
                  const d = new Date(v + 'Z');
                  return timeRange <= 24
                    ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    : d.toLocaleDateString([], { month: 'short', day: 'numeric' });
                }}
                tick={{ fontSize: 11, fill: 'var(--color-muted)' }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tickFormatter={v => `${v}ms`}
                tick={{ fontSize: 11, fill: 'var(--color-muted)' }}
                axisLine={false}
                tickLine={false}
                width={55}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="responseTime"
                stroke="#2563eb"
                strokeWidth={1.5}
                fill="url(#rtGrad)"
                dot={false}
                connectNulls={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Uptime History ────────────────────────────────────────────── */}
      <div className="chart-card">
        <div className="chart-header">
          <h2 className="chart-title">Uptime History</h2>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <UptimeBar segments={segments} maxSegments={90} />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontSize: '11px', color: 'var(--color-muted)' }}>
            <span>{timeRange}h ago</span>
            <span>Now</span>
          </div>
        </div>

        <table className="uptime-table">
          <tbody>
            <tr>
              <td>Last 24 hours</td>
              <td>{uptimeFor('uptime_24h')}</td>
            </tr>
            <tr>
              <td>Last 7 days</td>
              <td>{uptimeFor('uptime_7d')}</td>
            </tr>
            <tr>
              <td>Last 30 days</td>
              <td>{uptimeFor('uptime_30d')}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* ── Active Incidents ──────────────────────────────────────────── */}
      {incidents.filter(i => i.status === 'ongoing').length > 0 && (
        <div className="section-card">
          <div className="section-card-header">
            <span className="section-card-title" style={{ color: 'var(--color-down)' }}>
              Active Incident
            </span>
          </div>
          {incidents.filter(i => i.status === 'ongoing').map(inc => (
            <div key={inc.id} className="incident-item">
              <p style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--color-down)', marginBottom: 4 }}>
                ● Ongoing — {inc.reason}
              </p>
              <p style={{ fontSize: '12.5px', color: 'var(--color-muted)' }}>
                Started {timeAgo(inc.started_at)}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* ── Response Validation ──────────────────────────────────────── */}
      {(monitor.expected_status || monitor.expected_content) && (
        <div className="section-card">
          <div className="section-card-header">
            <span className="section-card-title">Validation Rules</span>
          </div>
          <div style={{ padding: '12px 16px', fontSize: '13px' }}>
            {monitor.expected_status && (
              <div style={{ marginBottom: '6px' }}>
                <span style={{ color: 'var(--color-muted)' }}>Expected Status: </span>
                <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{monitor.expected_status}</span>
                {monitor.last_status_code != null && (
                  <span style={{ marginLeft: '8px', color: monitor.last_status_code === monitor.expected_status ? 'var(--color-up)' : 'var(--color-down)' }}>
                    {monitor.last_status_code === monitor.expected_status ? '✓' : `✕ Got ${monitor.last_status_code}`}
                  </span>
                )}
              </div>
            )}
            {monitor.expected_content && (
              <div>
                <span style={{ color: 'var(--color-muted)' }}>Response Contains: </span>
                <code style={{ background: 'var(--color-bg)', padding: '1px 5px', borderRadius: 3, fontSize: '12px' }}>
                  {monitor.expected_content}
                </code>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Recent Checks ────────────────────────────────────────────── */}
      <div className="section-card">
        <div className="section-card-header">
          <span className="section-card-title">Recent Checks</span>
          <span style={{ fontSize: '12px', color: 'var(--color-muted)' }}>Click row to see details</span>
        </div>

        {checks.length === 0 ? (
          <div className="empty-state" style={{ padding: '32px' }}>
            <p style={{ color: 'var(--color-muted)', fontSize: '13.5px' }}>
              No checks recorded yet. First check is running…
            </p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table aria-label="Recent checks">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Status</th>
                  <th>Response</th>
                  <th>HTTP</th>
                  <th>Content</th>
                </tr>
              </thead>
              <tbody>
                {checks.map(c => <CheckRow key={c.id} check={c} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
