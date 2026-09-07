import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { monitors as monitorsApi } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import AddMonitorModal from '../components/AddMonitorModal';
import { timeAgo, formatResponseTime, formatUptime } from '../utils';

const STATUS_FILTERS = ['all', 'up', 'down', 'degraded', 'checking'];
const SORT_OPTIONS = [
  { label: 'Name',         value: 'name' },
  { label: 'Status',       value: 'status' },
  { label: 'Response time',value: 'response' },
  { label: 'Uptime',       value: 'uptime' },
  { label: 'Last checked', value: 'checked' },
];

function SortIcon({ active, asc }) {
  if (!active) return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ opacity: 0.3 }}>
      <path d="M7 15l5 5 5-5M7 9l5-5 5 5"/>
    </svg>
  );
  return asc ? (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 19V5M5 12l7-7 7 7"/>
    </svg>
  ) : (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12l7 7 7-7"/>
    </svg>
  );
}

function SkeletonRow() {
  return (
    <tr>
      {[200, 100, 80, 80, 120].map((w, i) => (
        <td key={i}>
          <span className="skeleton" style={{ width: w, height: 14, display: 'block' }} />
        </td>
      ))}
    </tr>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [monitorList, setMonitorList] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');
  const [showModal, setShowModal] = useState(false);

  const [search, setSearch]     = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sort, setSort]         = useState({ key: 'checked', asc: false });

  const load = useCallback(async () => {
    try {
      setError('');
      const data = await monitorsApi.list();
      setMonitorList(data);
    } catch (err) {
      setError('Unable to reach the server. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 15000); // auto-refresh every 15s
    return () => clearInterval(interval);
  }, [load]);

  // ── Summary stats ──────────────────────────────────────────────────────
  const total    = monitorList.length;
  const upCount  = monitorList.filter(m => m.last_status === 'up').length;
  const downCount= monitorList.filter(m => m.last_status === 'down').length;
  const degraded = monitorList.filter(m => m.last_status === 'degraded').length;

  const allResponseTimes = monitorList
    .filter(m => m.last_response_time != null)
    .map(m => m.last_response_time);
  const avgResponse = allResponseTimes.length
    ? Math.round(allResponseTimes.reduce((a, b) => a + b, 0) / allResponseTimes.length)
    : null;

  // ── Filter + sort ─────────────────────────────────────────────────────
  const filtered = monitorList
    .filter(m => {
      if (statusFilter !== 'all' && m.last_status !== statusFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        return m.name.toLowerCase().includes(q) || m.url.toLowerCase().includes(q);
      }
      return true;
    })
    .sort((a, b) => {
      let va, vb;
      switch (sort.key) {
        case 'name':     va = a.name; vb = b.name; break;
        case 'status':   va = a.last_status || ''; vb = b.last_status || ''; break;
        case 'response': va = a.last_response_time ?? Infinity; vb = b.last_response_time ?? Infinity; break;
        case 'uptime':   va = 0; vb = 0; break; // uptime requires per-monitor data
        case 'checked':  va = a.last_checked_at || ''; vb = b.last_checked_at || ''; break;
        default:         return 0;
      }
      if (va < vb) return sort.asc ? -1 : 1;
      if (va > vb) return sort.asc ?  1 : -1;
      return 0;
    });

  const toggleSort = (key) => {
    setSort(s => s.key === key ? { key, asc: !s.asc } : { key, asc: true });
  };

  return (
    <div className="page">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Monitor the health and performance of your services.</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowModal(true)}
          id="add-monitor-btn"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Add Monitor
        </button>
      </div>

      {error && (
        <div className="error-banner" role="alert">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {error}
          <button className="btn btn-ghost btn-sm" style={{ marginLeft: 'auto' }} onClick={load}>Retry</button>
        </div>
      )}

      {/* ── Summary Bar ─────────────────────────────────────────────── */}
      {!loading && total > 0 && (
        <div className="stats-row" role="region" aria-label="Summary statistics">
          <div className="stat-item">
            <span className="stat-value">{total}</span>
            <span className="stat-label">Monitors</span>
          </div>
          <div className="stat-divider" aria-hidden="true" />
          <div className="stat-item">
            <span className="stat-value up">{upCount}</span>
            <span className="stat-label">Up</span>
          </div>
          <div className="stat-item">
            <span className="stat-value down">{downCount}</span>
            <span className="stat-label">Down</span>
          </div>
          <div className="stat-item">
            <span className="stat-value degraded">{degraded}</span>
            <span className="stat-label">Degraded</span>
          </div>
          <div className="stat-divider" aria-hidden="true" />
          <div className="stat-item">
            <span className="stat-value">{avgResponse != null ? `${avgResponse} ms` : '—'}</span>
            <span className="stat-label">Avg Response</span>
          </div>
        </div>
      )}

      {/* ── Monitor Table ────────────────────────────────────────────── */}
      <div className="table-container">
        <div className="table-toolbar">
          {/* Search */}
          <div className="search-input">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
            <input
              type="search"
              placeholder="Search monitors…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              aria-label="Search monitors"
              id="monitor-search"
            />
          </div>

          {/* Status filters */}
          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }} role="group" aria-label="Filter by status">
            {STATUS_FILTERS.map(f => (
              <button
                key={f}
                className={`filter-btn${statusFilter === f ? ' active' : ''}`}
                onClick={() => setStatusFilter(f)}
                aria-pressed={statusFilter === f}
              >
                {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <table aria-label="Loading monitors" aria-busy="true">
            <thead>
              <tr>
                <th>Service</th><th>Status</th><th>Response</th><th>Uptime</th><th>Last Checked</th>
              </tr>
            </thead>
            <tbody>
              {[1,2,3].map(i => <SkeletonRow key={i} />)}
            </tbody>
          </table>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <svg className="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
            <p className="empty-state-title">
              {total === 0 ? 'No monitors yet.' : 'No matches found.'}
            </p>
            <p className="empty-state-desc">
              {total === 0
                ? 'Add your first API or website to start monitoring its health.'
                : 'Try adjusting your search or filter.'}
            </p>
            {total === 0 && (
              <button className="btn btn-primary" onClick={() => setShowModal(true)}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M12 5v14M5 12h14"/>
                </svg>
                Add Monitor
              </button>
            )}
          </div>
        ) : (
          <table aria-label="Monitor list">
            <thead>
              <tr>
                {[
                  { label: 'Service',      key: 'name' },
                  { label: 'Status',       key: 'status' },
                  { label: 'Response',     key: 'response' },
                  { label: 'Last Checked', key: 'checked' },
                ].map(col => (
                  <th
                    key={col.key}
                    onClick={() => toggleSort(col.key)}
                    aria-sort={sort.key === col.key ? (sort.asc ? 'ascending' : 'descending') : 'none'}
                    style={{ cursor: 'pointer' }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      {col.label}
                      <SortIcon active={sort.key === col.key} asc={sort.asc} />
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(m => (
                <tr
                  key={m.id}
                  onClick={() => navigate(`/monitors/${m.id}`)}
                  tabIndex={0}
                  onKeyDown={e => e.key === 'Enter' && navigate(`/monitors/${m.id}`)}
                  aria-label={`View details for ${m.name}`}
                >
                  <td>
                    <div className="td-service">{m.name}</div>
                    <div className="td-url">{m.url}</div>
                  </td>
                  <td>
                    <StatusBadge status={m.last_status || 'checking'} />
                  </td>
                  <td className="td-mono">
                    {formatResponseTime(m.last_response_time)}
                  </td>
                  <td style={{ color: 'var(--color-muted)', fontSize: '13px' }}>
                    {timeAgo(m.last_checked_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Add Modal ───────────────────────────────────────────────── */}
      {showModal && (
        <AddMonitorModal
          onClose={() => setShowModal(false)}
          onCreated={(m) => setMonitorList(list => [m, ...list])}
        />
      )}
    </div>
  );
}
