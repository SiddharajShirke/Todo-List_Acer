/**
 * AuthContext.jsx — Global auth state
 * - Reads token from localStorage on mount → calls /auth/me to rehydrate
 * - Exposes { user, loading, login, logout } via useAuth() hook
 * - Eliminates prop-drilling across pages
 */
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getToken, setToken, clearToken, getMe, demoLogin, logout as apiLogout } from '../services/api';
import { signInWithEmail, signUpWithEmail, exchangeSupabaseToken, supabaseSignOut } from '../services/supabase';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);
  const [loading, setLoading] = useState(true);

  // Rehydrate on mount if a token exists in localStorage or URL
  useEffect(() => {
    const init = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const urlToken = urlParams.get('token');
      if (urlToken) {
        setToken(urlToken);
        window.history.replaceState({}, document.title, window.location.pathname);
      }

      if (getToken()) {
        try {
          const me = await getMe();
          setUser(me);
        } catch {
          clearToken(); // token expired / invalid
        }
      }
      setLoading(false);
    };
    init();
  }, []);

  const login = useCallback(async () => {
    const res = await demoLogin();
    setToken(res.access_token);
    const me = await getMe();
    setUser(me);
    return me;
  }, []);

  const loginWithEmailPassword = useCallback(async (email, password) => {
    const { data, error } = await signInWithEmail(email, password);
    if (error) throw error;
    
    // Exchange for app JWT
    const { access_token, user: me } = await exchangeSupabaseToken(data.session.access_token);
    setToken(access_token);
    setUser(me);
    return me;
  }, []);

  const signupWithEmailPassword = useCallback(async (email, password) => {
    const { data, error } = await signUpWithEmail(email, password);
    if (error) throw error;
    
    // If email confirmation is off, this immediately logs them in
    if (data.session) {
      const { access_token, user: me } = await exchangeSupabaseToken(data.session.access_token);
      setToken(access_token);
      setUser(me);
      return { user: me, hasSession: true, token: access_token };
    }
    return { user: data.user, hasSession: false };
  }, []);

  const logout = useCallback(async () => {
    apiLogout();
    await supabaseSignOut().catch(() => {});
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithEmailPassword, signupWithEmailPassword, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
