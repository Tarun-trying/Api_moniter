import { useState, useEffect, useCallback } from 'react';
import { incidents as incidentsApi } from '../api/client';
import { timeAgo, formatDateTime, formatDuration } from '../utils';

function IncidentBadge({ status }) {
  const isOngoing = status === 'ongoing';
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '5px',
      fontSize: '12px',
      fontWeight: 600,
      color: isOngoing ? 'var(--color-down)' : 'var(--color-up)',
    }}>
      <span style={{
        width: 7, height: 7,
        borderRadius: '50%',
        background: isOngoing ? 'var(--color-down)' : 'var(--color-up)',
        display: 'inline-block',
      }} />
      {isOngoing ? 'Ongoing' : 'Resolved'}
    </span>
  );
}

export default function Incidents() {
  const [incidentList, setIncidentList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');
  const [filter,  setFilter]  = useState('all'); // 'all' | 'ongoing' | 'resolved'

  const load = useCallback(async () => {
    try {
      setError('');
      const data = await incidentsApi.list(filter === 'all' ? null : filter);
      setIncidentList(data);
    } catch (err) {
      setError('Unable to load incidents.');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Incidents</h1>
          <p className="page-subtitle">Automatically detected outages and degradations.</p>
        </div>
      </div>

      {error && (
        <div className="error-banner" role="alert">
          {error}
          <button className="btn btn-ghost btn-sm" style={{ marginLeft: 'auto' }} onClick={load}>Retry</button>
        </div>
      )}

      {/* Filter */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '16px' }} role="group" aria-label="Filter incidents">
        {['all', 'ongoing', 'resolved'].map(f => (
          <button
            key={f}
            className={`filter-btn${filter === f ? ' active' : ''}`}
            onClick={() => { setFilter(f); setLoading(true); }}
            aria-pressed={filter === f}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <div className="section-card">
        {loading ? (
          <div style={{ padding: '32px', textAlign: 'center' }}>
            <span className="spinner" />
          </div>
        ) : incidentList.length === 0 ? (
          <div className="empty-state">
            <svg className="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <p className="empty-state-title">No incidents</p>
            <p className="empty-state-desc">
              {filter === 'ongoing'
                ? 'No active incidents. All your services appear to be healthy.'
                : filter === 'resolved'
                ? 'No resolved incidents found.'
                : 'No incidents recorded. Incidents are automatically created after 3 consecutive failures.'}
            </p>
          </div>
        ) : (
          incidentList.map(inc => (
            <div key={inc.id} className="incident-item">
              <div className="incident-header">
                <span className="incident-monitor-name">{inc.monitor_name || `Monitor #${inc.monitor_id}`}</span>
                <IncidentBadge status={inc.status} />
              </div>

              {inc.monitor_url && (
                <div style={{ fontSize: '12px', color: 'var(--color-muted)', marginBottom: '6px', fontFamily: 'monospace' }}>
                  {inc.monitor_url}
                </div>
              )}

              <p className="incident-reason">{inc.reason}</p>

              <div className="incident-meta">
                <div className="incident-meta-item">
                  <span className="incident-meta-label">Started</span>
                  <span className="incident-meta-value">{formatDateTime(inc.started_at)}</span>
                </div>
                {inc.resolved_at && (
                  <div className="incident-meta-item">
                    <span className="incident-meta-label">Resolved</span>
                    <span className="incident-meta-value">{formatDateTime(inc.resolved_at)}</span>
                  </div>
                )}
                <div className="incident-meta-item">
                  <span className="incident-meta-label">Duration</span>
                  <span className="incident-meta-value">
                    {formatDuration(inc.started_at, inc.resolved_at)}
                    {inc.status === 'ongoing' && ' (ongoing)'}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
