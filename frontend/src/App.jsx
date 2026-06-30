import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Today from './pages/Today';
import Commitments from './pages/Commitments';
import Focus from './pages/Focus';
import Analytics from './pages/Analytics';

import WeeklyPlanning from './pages/WeeklyPlanning';
import WeeklyReview from './pages/WeeklyReview';
import Backlog from './pages/Backlog';

function AppRoutes() {
  const { user, loading, logout } = useAuth();

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: 'var(--color-bg)' }}>
        <div className="spinner" />
      </div>
    );
  }

  if (!user) return <Login />;

  return (
    <Routes>
      <Route path="/" element={<Layout user={user} onLogout={logout} />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard"   element={<Dashboard />} />
        <Route path="today"       element={<Today />} />
        <Route path="commitments" element={<Commitments />} />
        <Route path="focus"       element={<Focus />} />
        <Route path="analytics"   element={<Analytics />} />
        <Route path="weekly-planning" element={<WeeklyPlanning />} />
        <Route path="weekly-review"   element={<WeeklyReview />} />
        <Route path="backlog"         element={<Backlog />} />
      </Route>
    </Routes>
  );
}

import { StatsProvider } from './context/StatsContext';

function App() {
  return (
    <AuthProvider>
      <StatsProvider>
        <AppRoutes />
      </StatsProvider>
    </AuthProvider>
  );
}

export default App;
