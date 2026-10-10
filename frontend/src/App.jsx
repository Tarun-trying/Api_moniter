import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Sidebar from './components/Sidebar';
import MobileNav from './components/MobileNav';
import Dashboard from './pages/Dashboard';
import Monitors from './pages/Monitors';
import MonitorDetail from './pages/MonitorDetail';
import Incidents from './pages/Incidents';
import Analytics from './pages/Analytics';
import Login from './pages/Login';
import Register from './pages/Register';
import GoogleAuthCallback from './pages/GoogleAuthCallback';

/** Wraps routes that require authentication */
function PrivateRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="auth-loading">
        <div className="auth-callback-spinner" />
        <p>Loading…</p>
      </div>
    );
  }

  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

/** Main shell (sidebar + content) — only rendered when authenticated */
function AppShell() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content" id="main-content" role="main">
        <Routes>
          <Route path="/"               element={<Dashboard />} />
          <Route path="/monitors"       element={<Monitors />} />
          <Route path="/monitors/:id"   element={<MonitorDetail />} />
          <Route path="/incidents"      element={<Incidents />} />
          <Route path="/analytics"      element={<Analytics />} />
          <Route path="*" element={
            <div className="page">
              <div className="empty-state">
                <p className="empty-state-title">Page not found</p>
                <a href="/" className="btn btn-secondary">Go to Dashboard</a>
              </div>
            </div>
          } />
        </Routes>
      </main>
      <MobileNav />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login"           element={<Login />} />
          <Route path="/register"        element={<Register />} />
          <Route path="/auth/callback"   element={<GoogleAuthCallback />} />

          {/* Protected routes */}
          <Route path="/*" element={
            <PrivateRoute>
              <AppShell />
            </PrivateRoute>
          } />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
