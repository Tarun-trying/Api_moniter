import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { monitors as monitorsApi } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import AddMonitorModal from '../components/AddMonitorModal';
import { timeAgo, formatResponseTime } from '../utils';

export default function Monitors() {
  const navigate = useNavigate();
  const [monitorList, setMonitorList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');
  const [showModal, setShowModal] = useState(false);

  const load = useCallback(async () => {
    try {
      setError('');
      const data = await monitorsApi.list();
      setMonitorList(data);
    } catch (err) {
      setError('Unable to reach the server.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, [load]);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Monitors</h1>
          <p className="page-subtitle">All configured monitors and their current status.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)} id="monitors-add-btn">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          Add Monitor
        </button>
      </div>

      {error && <div className="error-banner" role="alert">{error}</div>}

      <div className="table-container">
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center' }}><span className="spinner" /></div>
        ) : monitorList.length === 0 ? (
          <div className="empty-state">
            <p className="empty-state-title">No monitors yet.</p>
            <p className="empty-state-desc">Add your first API or website to start monitoring.</p>
            <button className="btn btn-primary" onClick={() => setShowModal(true)}>Add Monitor</button>
          </div>
        ) : (
          <table aria-label="All monitors">
            <thead>
              <tr>
                <th>Service</th>
                <th>Status</th>
                <th>Method</th>
                <th>Interval</th>
                <th>Response</th>
                <th>Last Checked</th>
              </tr>
            </thead>
            <tbody>
              {monitorList.map(m => (
                <tr
                  key={m.id}
                  onClick={() => navigate(`/monitors/${m.id}`)}
                  tabIndex={0}
                  onKeyDown={e => e.key === 'Enter' && navigate(`/monitors/${m.id}`)}
                  aria-label={`View ${m.name}`}
                >
                  <td>
                    <div className="td-service">{m.name}</div>
                    <div className="td-url">{m.url}</div>
                  </td>
                  <td><StatusBadge status={m.last_status || 'checking'} /></td>
                  <td style={{ fontFamily: 'monospace', fontSize: '12.5px' }}>{m.method}</td>
                  <td style={{ color: 'var(--color-muted)', fontSize: '13px' }}>
                    {m.interval >= 3600 ? `${m.interval/3600}h` : m.interval >= 60 ? `${m.interval/60}m` : `${m.interval}s`}
                  </td>
                  <td className="td-mono">{formatResponseTime(m.last_response_time)}</td>
                  <td style={{ color: 'var(--color-muted)', fontSize: '13px' }}>{timeAgo(m.last_checked_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <AddMonitorModal
          onClose={() => setShowModal(false)}
          onCreated={(m) => setMonitorList(list => [m, ...list])}
        />
      )}
    </div>
  );
}
