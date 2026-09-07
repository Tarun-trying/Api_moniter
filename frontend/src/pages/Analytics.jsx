import { useState, useEffect, useCallback } from 'react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import { analytics as analyticsApi } from '../api/client';
import { formatResponseTime, formatUptime } from '../utils';

const TIME_RANGES = [
  { label: '24H', hours: 24  },
  { label: '7D',  hours: 168 },
  { label: '30D', hours: 720 },
];

function MetricCard({ label, value, sub }) {
  return (
    <div className="metric-item" style={{ background: 'var(--color-surface)' }}>
      <div className="metric-label">{label}</div>
      <div className="metric-value mono">{value}</div>
      {sub && <div style={{ fontSize: '11px', color: 'var(--color-muted)', marginTop: 3 }}>{sub}</div>}
    </div>
  );
}

function ChartTooltip({ active, payload, label, unit = '' }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      padding: '8px 12px',
      fontSize: '12.5px',
    }}>
      <p style={{ color: 'var(--color-muted)', marginBottom: 3 }}>
        {label ? new Date(label + 'Z').toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}
      </p>
      <p style={{ fontWeight: 600 }}>
        {payload[0]?.value != null ? `${Math.round(payload[0].value)}${unit}` : '—'}
      </p>
    </div>
  );
}

export default function Analytics() {
  const [data,    setData]    = useState(null);
  const [hours,   setHours]   = useState(24);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setError('');
      const d = await analyticsApi.get(hours);
      setData(d);
    } catch (err) {
      setError('Unable to load analytics data.');
    } finally {
      setLoading(false);
    }
  }, [hours]);

  useEffect(() => { load(); }, [load]);

  const tickFmt = (v) => {
    const d = new Date(v + 'Z');
    return hours <= 24
      ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      : d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Analytics</h1>
          <p className="page-subtitle">Aggregate performance and reliability metrics across all monitors.</p>
        </div>
        <div className="time-filters" role="group" aria-label="Time range">
          {TIME_RANGES.map(r => (
            <button
              key={r.hours}
              className={`time-filter-btn${hours === r.hours ? ' active' : ''}`}
              onClick={() => setHours(r.hours)}
              aria-pressed={hours === r.hours}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="error-banner" role="alert">{error}</div>}

      {/* ── Overview Metrics ──────────────────────────────────────────── */}
      <div className="analytics-grid" role="region" aria-label="Performance overview">
        <MetricCard
          label="Avg Response Time"
          value={data?.avg_response_time != null ? `${Math.round(data.avg_response_time)} ms` : '—'}
        />
        <MetricCard
          label="P95 Response Time"
          value={data?.p95_response_time != null ? `${Math.round(data.p95_response_time)} ms` : '—'}
          sub="95th percentile"
        />
        <MetricCard
          label="Overall Uptime"
          value={data?.uptime_percent != null ? formatUptime(data.uptime_percent) : '—'}
        />
        <MetricCard
          label="Total Checks"
          value={data?.total_checks?.toLocaleString() ?? '—'}
        />
        <MetricCard
          label="Total Failures"
          value={data?.total_failures?.toLocaleString() ?? '—'}
          sub={data?.total_checks ? `${((data.total_failures / data.total_checks) * 100).toFixed(2)}% failure rate` : undefined}
        />
        <MetricCard
          label="Incidents"
          value={data?.total_incidents?.toLocaleString() ?? '—'}
          sub={`in selected period`}
        />
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--color-muted)' }}>
          <span className="spinner" />
          <p style={{ marginTop: 12, fontSize: '13.5px' }}>Loading analytics…</p>
        </div>
      ) : (
        <>
          {/* ── Response Time Over Time ─────────────────────────────────── */}
          <div className="chart-card">
            <div className="chart-header">
              <h2 className="chart-title">Average Response Time</h2>
            </div>
            {!data?.response_over_time?.length ? (
              <div style={{ textAlign: 'center', padding: '40px', color: 'var(--color-muted)', fontSize: '13px' }}>
                No data for this period.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={data.response_over_time} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="anaGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563eb" stopOpacity={0.12} />
                      <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="time" tickFormatter={tickFmt} tick={{ fontSize: 11, fill: 'var(--color-muted)' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis tickFormatter={v => `${v}ms`} tick={{ fontSize: 11, fill: 'var(--color-muted)' }} axisLine={false} tickLine={false} width={55} />
                  <Tooltip content={<ChartTooltip unit=" ms" />} />
                  <Area type="monotone" dataKey="avg" stroke="#2563eb" strokeWidth={1.5} fill="url(#anaGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* ── Failures Over Time ─────────────────────────────────────── */}
          <div className="chart-card">
            <div className="chart-header">
              <h2 className="chart-title">Failures Over Time</h2>
            </div>
            {!data?.failure_over_time?.length ? (
              <div style={{ textAlign: 'center', padding: '40px', color: 'var(--color-muted)', fontSize: '13px' }}>
                No failures in this period.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={data.failure_over_time} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="time" tickFormatter={tickFmt} tick={{ fontSize: 11, fill: 'var(--color-muted)' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--color-muted)' }} axisLine={false} tickLine={false} width={30} allowDecimals={false} />
                  <Tooltip content={<ChartTooltip unit=" failures" />} />
                  <Bar dataKey="failures" fill="#ef4444" radius={[2, 2, 0, 0]} maxBarSize={20} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* ── Uptime by Monitor ─────────────────────────────────────── */}
          {data?.monitor_uptime?.length > 0 && (
            <div className="chart-card">
              <div className="chart-header">
                <h2 className="chart-title">Uptime by Monitor</h2>
              </div>
              <ResponsiveContainer width="100%" height={Math.max(160, data.monitor_uptime.length * 36)}>
                <BarChart
                  data={data.monitor_uptime}
                  layout="vertical"
                  margin={{ top: 4, right: 60, left: 4, bottom: 0 }}
                >
                  <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11, fill: 'var(--color-muted)' }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 12, fill: 'var(--color-text)' }} axisLine={false} tickLine={false} width={120} />
                  <Tooltip formatter={(v) => [`${v.toFixed(2)}%`, 'Uptime']} />
                  <Bar dataKey="uptime" radius={[0, 3, 3, 0]} maxBarSize={18}>
                    {data.monitor_uptime.map((entry, i) => (
                      <Cell key={i} fill={entry.uptime >= 99 ? '#16a34a' : entry.uptime >= 95 ? '#d97706' : '#dc2626'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}
