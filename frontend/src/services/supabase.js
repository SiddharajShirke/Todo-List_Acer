/**
 * supabase.js — Supabase Realtime & Auth Client (Frontend)
 *
 * This client is used for:
 *   1. Supabase Auth (sign up, sign in, sign out via Supabase)
 *   2. Realtime subscriptions (live updates when DB changes)
 *
 * NOT used for CRUD — all CRUD goes through the FastAPI backend via api.js.
 *
 * Usage:
 *   import { supabase, subscribeToTable } from './supabase';
 *
 * Auth flow (Supabase Auth):
 *   const { data, error } = await supabase.auth.signInWithPassword({ email, password });
 *   if (data.session) {
 *     // Send data.session.access_token to POST /auth/supabase to get our app JWT
 *   }
 */

import { createClient } from '@supabase/supabase-js';
import { useEffect } from 'react';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.warn(
    '[Supabase] VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY not set in frontend/.env. ' +
    'Realtime and Supabase Auth will not work. Add these after setting up your Supabase project.'
  );
}

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  realtime: {
    params: {
      eventsPerSecond: 10,
    },
  },
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: false, // We handle auth URL ourselves
  },
});


// ── Auth Helpers ───────────────────────────────────────────────────────────────

/**
 * Sign up with email/password via Supabase Auth.
 * After sign-up, call exchangeSupabaseToken() to get our app JWT.
 */
export const signUpWithEmail = (email, password) =>
  supabase.auth.signUp({ email, password });

/**
 * Sign in with email/password via Supabase Auth.
 */
export const signInWithEmail = (email, password) =>
  supabase.auth.signInWithPassword({ email, password });

/**
 * Send magic link to email (passwordless sign-in).
 */
export const signInWithMagicLink = (email) =>
  supabase.auth.signInWithOtp({ email });

/**
 * Sign out from Supabase Auth.
 */
export const supabaseSignOut = () => supabase.auth.signOut();

/**
 * Get the current Supabase Auth session.
 */
export const getSupabaseSession = () => supabase.auth.getSession();

/**
 * Exchange a Supabase access_token for our FastAPI app JWT.
 * Call this after any Supabase sign-in.
 *
 * @param {string} supabaseAccessToken - The access_token from Supabase Auth session
 * @returns {Promise<{access_token: string, user: object}>}
 */
export const exchangeSupabaseToken = async (supabaseAccessToken) => {
  const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const res = await fetch(`${BASE_URL}/auth/supabase`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ supabase_access_token: supabaseAccessToken }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Auth exchange failed: HTTP ${res.status}`);
  }
  return res.json();
};


// ── Realtime Subscription Helpers ─────────────────────────────────────────────

/**
 * Subscribe to realtime changes on a specific table.
 *
 * @param {string} table - Table name (e.g., 'tasks', 'daily_plans')
 * @param {Function} onInsert - Called with new row on INSERT
 * @param {Function} onUpdate - Called with updated row on UPDATE
 * @param {Function} onDelete - Called with deleted row info on DELETE
 * @param {string} [filter] - Optional Supabase filter (e.g., 'user_id=eq.123')
 * @returns {Function} unsubscribe - Call to clean up the subscription
 *
 * Example:
 *   const unsub = subscribeToTable('tasks',
 *     (row) => setTasks(prev => [...prev, row]),
 *     (row) => setTasks(prev => prev.map(t => t.id === row.id ? row : t)),
 *     (row) => setTasks(prev => prev.filter(t => t.id !== row.id))
 *   );
 *   return () => unsub(); // cleanup in useEffect
 */
export const subscribeToTable = (table, onInsert, onUpdate, onDelete, filter = null) => {
  const channelName = `realtime:${table}:${Date.now()}`;
  let channelConfig = supabase.channel(channelName);

  const eventConfig = filter
    ? { event: '*', schema: 'public', table, filter }
    : { event: '*', schema: 'public', table };

  channelConfig = channelConfig.on('postgres_changes', eventConfig, (payload) => {
    const { eventType, new: newRecord, old: oldRecord } = payload;
    if (eventType === 'INSERT' && onInsert) onInsert(newRecord);
    if (eventType === 'UPDATE' && onUpdate) onUpdate(newRecord);
    if (eventType === 'DELETE' && onDelete) onDelete(oldRecord);
  });

  const subscription = channelConfig.subscribe((status) => {
    if (status === 'SUBSCRIBED') {
      console.debug(`[Realtime] Subscribed to ${table}`);
    }
    if (status === 'CHANNEL_ERROR') {
      console.error(`[Realtime] Channel error on ${table}`);
    }
  });

  // Return unsubscribe function
  return () => {
    supabase.removeChannel(subscription);
    console.debug(`[Realtime] Unsubscribed from ${table}`);
  };
};


/**
 * Subscribe to a single table with a user_id filter.
 * Convenience wrapper around subscribeToTable for user-scoped data.
 *
 * @param {string} table - Table name
 * @param {number} userId - The user's app ID (NOT supabase UUID)
 * @param {Function} onInsert
 * @param {Function} onUpdate
 * @param {Function} onDelete
 * @returns {Function} unsubscribe
 */
export const subscribeToUserTable = (table, userId, onInsert, onUpdate, onDelete) => {
  return subscribeToTable(table, onInsert, onUpdate, onDelete, `user_id=eq.${userId}`);
};


/**
 * React hook: use realtime subscription with automatic cleanup.
 * Import and use in any component.
 *
 * Example:
 *   useRealtimeTable('tasks', userId,
 *     (row) => setTasks(prev => [...prev, row]),
 *     (row) => setTasks(prev => prev.map(t => t.id === row.id ? row : t)),
 *     (row) => setTasks(prev => prev.filter(t => t.id !== row.id))
 *   );
 */
export const useRealtimeTable = (table, userId, onInsert, onUpdate, onDelete) => {
  useEffect(() => {
    if (!userId || !SUPABASE_URL) return;
    const unsubscribe = subscribeToUserTable(table, userId, onInsert, onUpdate, onDelete);
    return unsubscribe;
  }, [table, userId]);
};
