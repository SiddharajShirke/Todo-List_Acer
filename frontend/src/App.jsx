import { Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { getToken, getMe } from './services/api';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Commitments from './pages/Commitments';
import Focus from './pages/Focus';
import Analytics from './pages/Analytics';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const init = async () => {
      if (getToken()) {
        try {
          const userData = await getMe();
          setUser(userData);
          setIsAuthenticated(true);
        } catch (e) {
          console.error("Not authenticated", e);
        }
      }
      setLoading(false);
    };
    init();
  }, []);

  if (loading) return <div>Loading...</div>;

  if (!isAuthenticated) {
    return <Login onLogin={(u) => { setUser(u); setIsAuthenticated(true); }} />;
  }

  return (
    <Routes>
      <Route path="/" element={<Layout user={user} onLogout={() => { setUser(null); setIsAuthenticated(false); }} />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard user={user} />} />
        <Route path="commitments" element={<Commitments />} />
        <Route path="focus" element={<Focus />} />
        <Route path="analytics" element={<Analytics />} />
      </Route>
    </Routes>
  );
}

export default App;
