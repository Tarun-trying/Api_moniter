import { useState } from 'react';

function SettingsRow({ label, desc, children }) {
  return (
    <div className="settings-row">
      <div>
        <div className="settings-row-label">{label}</div>
        {desc && <div className="settings-row-desc">{desc}</div>}
      </div>
      <div>{children}</div>
    </div>
  );
}

function Toggle({ id, checked, onChange }) {
  return (
    <label className="toggle" htmlFor={id}>
      <input id={id} type="checkbox" checked={checked} onChange={onChange} />
      <span className="toggle-slider" />
    </label>
  );
}

const INTERVAL_OPTIONS = [
  { label: '1 minute',   value: 60 },
  { label: '5 minutes',  value: 300 },
  { label: '10 minutes', value: 600 },
  { label: '15 minutes', value: 900 },
  { label: '30 minutes', value: 1800 },
  { label: '1 hour',     value: 3600 },
];

export default function Settings() {
  const [defaultInterval, setDefaultInterval] = useState(300);
  const [defaultTimeout,  setDefaultTimeout]  = useState(10);
  const [theme,           setTheme]           = useState('system');
  const [notifyOnDown,    setNotifyOnDown]    = useState(false);
  const [notifyOnRecover, setNotifyOnRecover] = useState(false);
  const [saved,           setSaved]           = useState(false);

  const handleSave = () => {
    // In V1, settings are stored locally (no backend persistence yet)
    localStorage.setItem('pm_settings', JSON.stringify({
      defaultInterval,
      defaultTimeout,
      theme,
      notifyOnDown,
      notifyOnRecover,
    }));
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Configure default monitoring behavior and preferences.</p>
        </div>
        <button className="btn btn-primary" onClick={handleSave} id="save-settings-btn">
          {saved ? (
            <>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              Saved
            </>
          ) : 'Save Changes'}
        </button>
      </div>

      {/* ── Monitoring Defaults ───────────────────────────────────────── */}
      <div className="settings-section">
        <div className="settings-section-title">Monitoring Defaults</div>

        <SettingsRow
          label="Default Check Interval"
          desc="Applied when creating a new monitor unless overridden."
        >
          <select
            className="form-select"
            style={{ width: 'auto' }}
            value={defaultInterval}
            onChange={e => setDefaultInterval(Number(e.target.value))}
            aria-label="Default check interval"
            id="settings-interval"
          >
            {INTERVAL_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </SettingsRow>

        <SettingsRow
          label="Default Timeout"
          desc="Seconds before a check is considered timed out."
        >
          <select
            className="form-select"
            style={{ width: 'auto' }}
            value={defaultTimeout}
            onChange={e => setDefaultTimeout(Number(e.target.value))}
            aria-label="Default timeout"
            id="settings-timeout"
          >
            {[5,10,15,20,30,60].map(t => (
              <option key={t} value={t}>{t} seconds</option>
            ))}
          </select>
        </SettingsRow>
      </div>

      {/* ── Appearance ───────────────────────────────────────────────── */}
      <div className="settings-section">
        <div className="settings-section-title">Appearance</div>

        <SettingsRow label="Theme" desc="Affects the overall color scheme of the interface.">
          <select
            className="form-select"
            style={{ width: 'auto' }}
            value={theme}
            onChange={e => setTheme(e.target.value)}
            aria-label="Theme preference"
            id="settings-theme"
          >
            <option value="system">System</option>
            <option value="light">Light</option>
            <option value="dark">Dark (coming soon)</option>
          </select>
        </SettingsRow>
      </div>

      {/* ── Notifications ─────────────────────────────────────────────── */}
      <div className="settings-section">
        <div className="settings-section-title">Notifications</div>
        <div style={{ padding: '10px 16px', background: '#fffbeb', borderBottom: '1px solid var(--color-border)' }}>
          <span style={{ fontSize: '12.5px', color: 'var(--color-degraded)' }}>
            ⚠ Notification delivery (email, webhook, Slack) is planned for a future version. Toggle settings are saved but not yet active.
          </span>
        </div>

        <SettingsRow
          label="Alert on Service Down"
          desc="Notify when a monitor's status changes to DOWN."
        >
          <Toggle
            id="notify-down"
            checked={notifyOnDown}
            onChange={e => setNotifyOnDown(e.target.checked)}
          />
        </SettingsRow>

        <SettingsRow
          label="Alert on Recovery"
          desc="Notify when a previously DOWN monitor comes back up."
        >
          <Toggle
            id="notify-recover"
            checked={notifyOnRecover}
            onChange={e => setNotifyOnRecover(e.target.checked)}
          />
        </SettingsRow>
      </div>

      {/* ── About ─────────────────────────────────────────────────────── */}
      <div className="settings-section">
        <div className="settings-section-title">About</div>
        <SettingsRow label="Version" desc="">
          <span style={{ fontSize: '13px', color: 'var(--color-muted)', fontFamily: 'monospace' }}>v1.0.0</span>
        </SettingsRow>
        <SettingsRow label="Backend" desc="">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="btn btn-secondary btn-sm"
          >
            API Docs ↗
          </a>
        </SettingsRow>
      </div>
    </div>
  );
}
