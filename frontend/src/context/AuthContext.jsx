import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { auth as authApi } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('pm_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  // On mount, verify the token is still valid
  useEffect(() => {
    const token = localStorage.getItem('pm_token');
    if (!token) {
      setLoading(false);
      return;
    }
    authApi.me()
      .then((u) => {
        setUser(u);
        localStorage.setItem('pm_user', JSON.stringify(u));
      })
      .catch(() => {
        // Token invalid — clear everything
        localStorage.removeItem('pm_token');
        localStorage.removeItem('pm_user');
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await authApi.login({ email, password });
    localStorage.setItem('pm_token', data.access_token);
    localStorage.setItem('pm_user', JSON.stringify(data.user));
    setUser(data.user);
    return data.user;
  }, []);

  const register = useCallback(async (name, email, password) => {
    const data = await authApi.register({ name, email, password });
    localStorage.setItem('pm_token', data.access_token);
    localStorage.setItem('pm_user', JSON.stringify(data.user));
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try { await authApi.logout(); } catch (_) {}
    localStorage.removeItem('pm_token');
    localStorage.removeItem('pm_user');
    setUser(null);
  }, []);

  const loginWithGoogle = useCallback(() => {
    window.location.href = authApi.googleUrl();
  }, []);

  // Called from the OAuth callback page
  const setTokenFromCallback = useCallback(async (token) => {
    localStorage.setItem('pm_token', token);
    const u = await authApi.me();
    localStorage.setItem('pm_user', JSON.stringify(u));
    setUser(u);
    return u;
  }, []);

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      isAuthenticated: !!user,
      login,
      register,
      logout,
      loginWithGoogle,
      setTokenFromCallback,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
