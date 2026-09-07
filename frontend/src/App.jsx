import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import MobileNav from './components/MobileNav';
import Dashboard from './pages/Dashboard';
import Monitors from './pages/Monitors';
import MonitorDetail from './pages/MonitorDetail';
import Incidents from './pages/Incidents';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <main className="main-content" id="main-content" role="main">
          <Routes>
            <Route path="/"                  element={<Dashboard />} />
            <Route path="/monitors"          element={<Monitors />} />
            <Route path="/monitors/:id"      element={<MonitorDetail />} />
            <Route path="/incidents"         element={<Incidents />} />
            <Route path="/analytics"         element={<Analytics />} />
            <Route path="/settings"          element={<Settings />} />
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
    </BrowserRouter>
  );
}
