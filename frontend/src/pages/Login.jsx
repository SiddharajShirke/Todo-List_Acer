import { useState } from 'react';
import { demoLogin, setToken, getMe } from '../services/api';

function Login({ onLogin }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleDemoLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await demoLogin();
      setToken(res.access_token);
      const user = await getMe();
      onLogin(user);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div id="login-page" className="page">
      <div className="login-container">
        <h1>AI Productivity Assistant</h1>
        <p>Organize, prioritize, and focus with AI.</p>
        {error && <p style={{ color: 'var(--color-danger)' }}>{error}</p>}
        <button 
          onClick={handleDemoLogin} 
          className="btn btn-primary"
          disabled={loading}
        >
          {loading ? 'Logging in...' : 'Try Demo'}
        </button>
      </div>
    </div>
  );
}

export default Login;
