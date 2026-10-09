/**
 * Centralized API client for API Monitoring System.
 * All fetch calls go through here — no scattered fetch() across components.
 */

// In production, API_URL points to the deployed backend (e.g. https://api.myapp.com).
// In development, Vite's proxy forwards /api → http://localhost:8000.
const BASE = import.meta.env.API_URL
  ? `${import.meta.env.API_URL}/api`
  : '/api';


async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      detail = json.detail || detail;
    } catch (_) {}
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }

  if (res.status === 204) return null;
  return res.json();
}

// ── Monitors ──────────────────────────────────────────────────────────────
export const monitors = {
  list:   ()         => request('/monitors'),
  get:    (id)       => request(`/monitors/${id}`),
  create: (data)     => request('/monitors', { method: 'POST', body: data }),
  update: (id, data) => request(`/monitors/${id}`, { method: 'PUT', body: data }),
  delete: (id)       => request(`/monitors/${id}`, { method: 'DELETE' }),
  check:  (id)       => request(`/monitors/${id}/check`, { method: 'POST' }),
};

// ── Checks ────────────────────────────────────────────────────────────────
export const checks = {
  list:     (id, limit = 50) => request(`/monitors/${id}/checks?limit=${limit}`),
  uptime:   (id)             => request(`/monitors/${id}/uptime`),
  segments: (id, hours = 24) => request(`/monitors/${id}/uptime/segments?hours=${hours}`),
  chart:    (id, hours = 24) => request(`/monitors/${id}/chart?hours=${hours}`),
};

// ── Incidents ─────────────────────────────────────────────────────────────
export const incidents = {
  list:       (status)  => request(`/incidents${status ? `?status=${status}` : ''}`),
  forMonitor: (id)      => request(`/monitors/${id}/incidents`),
};

// ── Analytics ─────────────────────────────────────────────────────────────
export const analytics = {
  get: (hours = 24) => request(`/analytics?hours=${hours}`),
};
