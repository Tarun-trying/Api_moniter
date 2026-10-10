/**
 * Centralized API client for API Monitoring System.
 * Auto-attaches Authorization header from localStorage JWT.
 */

const rawApiUrl = import.meta.env.VITE_API_URL || import.meta.env.API_URL;
const BASE = rawApiUrl ? `${rawApiUrl.replace(/\/$/, '')}/api` : '/api';

function getToken() {
  return localStorage.getItem('pm_token');
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      detail = json.detail || detail;
    } catch (_) {}

    if (res.status === 401 && !path.startsWith('/auth/login') && !path.startsWith('/auth/register')) {
      localStorage.removeItem('pm_token');
      localStorage.removeItem('pm_user');
      if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        window.location.href = '/login';
      }
    }

    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }

  if (res.status === 204) return null;
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────
export const auth = {
  register: (data) => request('/auth/register', { method: 'POST', body: data }),
  login:    (data) => request('/auth/login',    { method: 'POST', body: data }),
  me:       ()     => request('/auth/me'),
  logout:   ()     => request('/auth/logout',   { method: 'POST' }),
  googleUrl: () => `${BASE}/auth/google`,
};

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
