/**
 * GoogleAuthCallback — handles the redirect from the backend after Google OAuth.
 * The backend sends: /auth/callback?token=<jwt>
 * This page extracts the token, stores it, then navigates to the dashboard.
 */
import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function GoogleAuthCallback() {
  const [searchParams] = useSearchParams();
  const { setTokenFromCallback } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    const err   = searchParams.get('error');

    if (err || !token) {
      setError(
        err === 'google_denied'  ? 'Google sign-in was cancelled.' :
        err === 'google_failed'  ? 'Google sign-in failed. Please try again.' :
        err === 'google_userinfo'? 'Could not retrieve Google profile.' :
        'Authentication failed. Please try again.'
      );
      return;
    }

    setTokenFromCallback(token)
      .then(() => navigate('/', { replace: true }))
      .catch(() => setError('Failed to authenticate. Please try again.'));
  }, []);

  if (error) {
    return (
      <div className="auth-page">
        <div className="auth-bg">
          <div className="auth-orb auth-orb-1" />
          <div className="auth-orb auth-orb-2" />
        </div>
        <div className="auth-card-wrapper">
          <div className="auth-card" style={{ textAlign: 'center', padding: '40px 32px' }}>
            <div style={{ fontSize: 40, marginBottom: 16 }}>⚠️</div>
            <h2 style={{ marginBottom: 8, fontSize: 18, fontWeight: 600 }}>Sign-in failed</h2>
            <p style={{ color: 'var(--color-muted)', marginBottom: 24, fontSize: 14 }}>{error}</p>
            <a href="/login" className="auth-submit-btn" style={{ display: 'inline-flex', justifyContent: 'center' }}>
              Back to Login
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-bg">
        <div className="auth-orb auth-orb-1" />
        <div className="auth-orb auth-orb-2" />
      </div>
      <div className="auth-card-wrapper">
        <div className="auth-card" style={{ textAlign: 'center', padding: '48px 32px' }}>
          <div className="auth-logo" style={{ justifyContent: 'center', marginBottom: 24 }}>
            <div className="auth-logo-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
            </div>
            <span className="auth-logo-text">PulseMonitor</span>
          </div>
          <div className="auth-callback-spinner" />
          <p style={{ color: 'var(--color-muted)', marginTop: 16, fontSize: 14 }}>
            Completing sign-in…
          </p>
        </div>
      </div>
    </div>
  );
}
