import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import './Login.css';

function Login() {
  const { loginWithEmailPassword, signupWithEmailPassword, login } = useAuth();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      if (isSignUp) {
        const result = await signupWithEmailPassword(email, password);
        // Supabase might require email confirmation depending on settings
        if (result.hasSession) {
           setSuccessMsg('Account created! Connecting your Google Calendar...');
           setTimeout(() => {
             window.location.href = `http://localhost:8000/auth/google/login?token=${result.token}`;
           }, 1000);
        } else {
           setSuccessMsg('Account created! Please check your email to sign in.');
           setIsSignUp(false);
        }
      } else {
        await loginWithEmailPassword(email, password);
      }
    } catch (err) {
      setError(err.message || 'An error occurred during authentication.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    // Keep the original backend flow for Google OAuth
    window.location.href = 'http://localhost:8000/auth/google/login';
  };

  return (
    <div id="login-page">
      {/* Decorative animated background */}
      <div className="login-bg-blob blob-1"></div>
      <div className="login-bg-blob blob-2"></div>
      
      <div className="login-split-container">
        
        {/* Left Side: Branding / Showcase */}
        <div className="login-showcase">
          <div className="showcase-content">
            <div className="login-logo">
              <span style={{ fontSize: '4rem' }}>🎯</span>
            </div>
            <h1>AI Productivity Assistant</h1>
            <p className="showcase-subtitle">
              Organize, prioritize, and focus — powered by intelligent systems that adapt to your workflow.
            </p>
            
            <div className="showcase-features">
              <div className="feature-item">
                <span className="feature-icon">⚡</span>
                <div>
                  <strong>Real-time Sync</strong>
                  <p>Updates instantly across all your devices.</p>
                </div>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🧠</span>
                <div>
                  <strong>AI Summaries</strong>
                  <p>Smart daily reviews and coaching insights.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Auth Form */}
        <div className="login-form-container">
          <div className="form-glass-panel">
            <h2>{isSignUp ? 'Create an Account' : 'Welcome Back'}</h2>
            <p className="login-muted-text">
              {isSignUp ? 'Sign up to start organizing your life.' : 'Sign in to access your dashboard.'}
            </p>

            {error && <div className="auth-error-banner">{error}</div>}
            {successMsg && <div className="auth-success-banner">{successMsg}</div>}

            <form onSubmit={handleSubmit} className="auth-form">
              <div className="input-group">
                <label>Email Address</label>
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com" 
                  required 
                />
              </div>
              <div className="input-group">
                <label>Password</label>
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••" 
                  required 
                  minLength={6}
                />
              </div>
              
              <button type="submit" className="btn btn-primary auth-submit-btn" disabled={loading}>
                {loading ? <span className="spinner-sm"></span> : (isSignUp ? 'Sign Up' : 'Sign In')}
              </button>
            </form>

            <div className="auth-divider">
              <span>or continue with</span>
            </div>

            <div className="social-auth">
              <button onClick={handleGoogleLogin} className="btn btn-ghost google-btn">
                <svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Google
              </button>
            </div>

            <div className="auth-footer">
              {isSignUp ? (
                <p>Already have an account? <button type="button" className="text-link" onClick={() => setIsSignUp(false)}>Sign In</button></p>
              ) : (
                <p>Don't have an account? <button type="button" className="text-link" onClick={() => setIsSignUp(true)}>Sign Up</button></p>
              )}
            </div>
            
            {/* Fallback demo login if they don't want to make an account */}
            <div className="demo-login-wrapper">
               <button type="button" className="text-link login-muted-text" onClick={login} style={{ fontSize: '0.8rem', marginTop: '16px' }}>
                 Use demo account instead
               </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;
