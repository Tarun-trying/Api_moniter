import { useState } from 'react';
import Modal from './Modal';
import { monitors as monitorsApi } from '../api/client';

const INTERVALS = [
  { label: '30 seconds', value: 30 },
  { label: '1 minute',   value: 60 },
  { label: '2 minutes',  value: 120 },
  { label: '5 minutes',  value: 300 },
  { label: '10 minutes', value: 600 },
  { label: '15 minutes', value: 900 },
  { label: '30 minutes', value: 1800 },
  { label: '1 hour',     value: 3600 },
];

const TIMEOUTS = [5, 10, 15, 20, 30, 60];

const DEFAULT_FORM = {
  name: '',
  url: '',
  method: 'GET',
  interval: 300,
  timeout: 10,
  expected_status: 200,
  expected_content: '',
  showAdvanced: false,
};

export default function AddMonitorModal({ onClose, onCreated }) {
  const [form, setForm] = useState(DEFAULT_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const set = (key, value) => setForm(f => ({ ...f, [key]: value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Basic client-side validation
    if (!form.name.trim()) { setError('Name is required.'); return; }
    if (!form.url.trim())  { setError('URL is required.'); return; }
    if (!/^https?:\/\/.+/i.test(form.url.trim())) {
      setError('Please enter a valid HTTP or HTTPS URL.'); return;
    }

    setLoading(true);
    try {
      const payload = {
        name: form.name.trim(),
        url:  form.url.trim(),
        method: form.method,
        interval: Number(form.interval),
        timeout:  Number(form.timeout),
        expected_status: Number(form.expected_status) || 200,
        expected_content: form.expected_content.trim() || null,
      };
      const monitor = await monitorsApi.create(payload);
      onCreated(monitor);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to create monitor.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="Add Monitor"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button
            type="submit"
            form="add-monitor-form"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? <><span className="spinner" /> Creating…</> : 'Create Monitor'}
          </button>
        </>
      }
    >
      <form id="add-monitor-form" onSubmit={handleSubmit} noValidate>
        {error && (
          <div className="error-banner" role="alert">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            {error}
          </div>
        )}

        <div className="form-group">
          <label className="form-label" htmlFor="mon-name">Name</label>
          <input
            id="mon-name"
            className="form-input"
            placeholder="My API"
            value={form.name}
            onChange={e => set('name', e.target.value)}
            required
            autoFocus
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="mon-url">URL</label>
          <input
            id="mon-url"
            className="form-input"
            type="url"
            placeholder="https://api.example.com/health"
            value={form.url}
            onChange={e => set('url', e.target.value)}
            required
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div className="form-group">
            <label className="form-label" htmlFor="mon-interval">Check Interval</label>
            <select
              id="mon-interval"
              className="form-select"
              value={form.interval}
              onChange={e => set('interval', e.target.value)}
            >
              {INTERVALS.map(i => (
                <option key={i.value} value={i.value}>{i.label}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="mon-timeout">Timeout</label>
            <select
              id="mon-timeout"
              className="form-select"
              value={form.timeout}
              onChange={e => set('timeout', e.target.value)}
            >
              {TIMEOUTS.map(t => (
                <option key={t} value={t}>{t} seconds</option>
              ))}
            </select>
          </div>
        </div>

        {/* Advanced toggle */}
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          style={{ marginBottom: '4px', padding: '4px 0' }}
          onClick={() => set('showAdvanced', !form.showAdvanced)}
        >
          <svg
            width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
            style={{ transform: form.showAdvanced ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s' }}
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
          {form.showAdvanced ? 'Hide' : 'Show'} Advanced Options
        </button>

        {form.showAdvanced && (
          <div style={{ paddingTop: '8px', borderTop: '1px solid var(--color-border)', marginTop: '4px' }}>
            <div className="form-group">
              <label className="form-label" htmlFor="mon-status">Expected Status Code</label>
              <input
                id="mon-status"
                className="form-input"
                type="number"
                min="100" max="599"
                value={form.expected_status}
                onChange={e => set('expected_status', e.target.value)}
              />
              <span className="form-hint">Default: 200</span>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" htmlFor="mon-content">Expected Response Contains</label>
              <input
                id="mon-content"
                className="form-input"
                placeholder={`"status": "ok"`}
                value={form.expected_content}
                onChange={e => set('expected_content', e.target.value)}
              />
              <span className="form-hint">Mark as degraded if response body doesn't include this string.</span>
            </div>
          </div>
        )}
      </form>
    </Modal>
  );
}
