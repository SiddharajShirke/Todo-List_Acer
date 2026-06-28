/**
 * api.js — Centralised FastAPI Backend Client
 *
 * All CRUD operations go through FastAPI (not directly to Supabase).
 * Supabase Realtime subscriptions are handled in supabase.js.
 *
 * - Base URL from VITE_API_URL env var
 * - JWT stored in localStorage, attached to all requests
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'auth_token';

// ── Token helpers ──────────────────────────────────────────────────────────────
export const setToken = (t) => {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
};
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

// ── Core request helper ────────────────────────────────────────────────────────
async function req(method, path, body) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(BASE_URL + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

// ── Auth ───────────────────────────────────────────────────────────────────────
export const demoLogin = () => req('POST', '/auth/demo-login');
export const getMe = () => req('GET', '/auth/me');
export const updatePreferences = (preferences) => req('PATCH', '/auth/me/preferences', { preferences });
export const logout = () => clearToken();

/** Exchange Supabase Auth JWT for our app JWT */
export const supabaseLogin = (supabaseAccessToken) =>
  req('POST', '/auth/supabase', { supabase_access_token: supabaseAccessToken });

// ── Commitments ────────────────────────────────────────────────────────────────
export const ingestCommitment = (rawText, source = 'manual') =>
  req('POST', '/api/commitments/ingest', { raw_text: rawText, source });
export const createManual = (data) => req('POST', '/api/commitments/manual', data);
export const getCommitments = () => req('GET', '/api/commitments');
export const getCommitment = (id) => req('GET', `/api/commitments/${id}`);
export const markDone = (id) => req('PATCH', `/api/commitments/${id}/done`);
export const deleteCommitment = (id) => req('DELETE', `/api/commitments/${id}`);

// ── Tasks ──────────────────────────────────────────────────────────────────────
export const getTasks = (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.planned_date) params.set('planned_date', filters.planned_date);
  if (filters.weekly_plan_id != null) params.set('weekly_plan_id', filters.weekly_plan_id);
  if (filters.daily_plan_id != null) params.set('daily_plan_id', filters.daily_plan_id);
  if (filters.commitment_id != null) params.set('commitment_id', filters.commitment_id);
  if (filters.channel_id != null) params.set('channel_id', filters.channel_id);
  if (filters.is_done != null) params.set('is_done', filters.is_done);
  const qs = params.toString();
  return req('GET', `/api/tasks${qs ? '?' + qs : ''}`);
};
export const createTask = (data) => req('POST', '/api/tasks', data);
export const updateTask = (taskId, data) => req('PUT', `/api/tasks/${taskId}`, data);
export const markTaskDone = (taskId) => req('PATCH', `/api/tasks/${taskId}/done`);
export const markTaskUndone = (taskId) => req('PATCH', `/api/tasks/${taskId}/undone`);
export const deleteTask = (taskId) => req('DELETE', `/api/tasks/${taskId}`);
export const reorderTasks = (taskOrders) => req('PATCH', '/api/tasks/bulk/reorder', taskOrders);
export const getTaskStats = () => req('GET', '/api/tasks/stats/today');
export const getRecoveryPlan = (commitmentId) => req('GET', `/api/tasks/${commitmentId}/recovery-plan`);

// ── Daily Plans (NEW) ──────────────────────────────────────────────────────────
export const getTodayPlan = () => req('GET', '/api/daily-plans/today');
export const getDailyPlanByDate = (date) => req('GET', `/api/daily-plans/date/${date}`);
export const getDailyPlans = (limit = 30, offset = 0) =>
  req('GET', `/api/daily-plans?limit=${limit}&offset=${offset}`);
export const createDailyPlan = (data) => req('POST', '/api/daily-plans', data);
export const updateDailyPlan = (planId, data) => req('PATCH', `/api/daily-plans/${planId}`, data);
export const completeDailyPlan = (planId, notes = null, moodEnd = null) => {
  const params = new URLSearchParams();
  if (notes) params.set('notes', notes);
  if (moodEnd) params.set('mood_end', moodEnd);
  const qs = params.toString();
  return req('PATCH', `/api/daily-plans/${planId}/complete${qs ? '?' + qs : ''}`);
};
export const deleteDailyPlan = (planId) => req('DELETE', `/api/daily-plans/${planId}`);
export const getDailyPlanStats = (planId) => req('GET', `/api/daily-plans/${planId}/stats`);

// ── Weekly Plans ───────────────────────────────────────────────────────────────
// Uses /api/weekly-plans (also accessible via /api/weekly-objectives for backward compat)
export const getWeeklyPlans = () => req('GET', '/api/weekly-plans');
export const createWeeklyPlan = (data) => req('POST', '/api/weekly-plans', data);
export const updateWeeklyPlan = (planId, data) => req('PUT', `/api/weekly-plans/${planId}`, data);
export const deleteWeeklyPlan = (planId) => req('DELETE', `/api/weekly-plans/${planId}`);
export const getWeeklyPlansByWeek = (weekStart) =>
  req('GET', `/api/weekly-plans/by-week?week_start=${weekStart}`);

// Legacy aliases (keeps existing frontend code working during migration)
export const getObjectives = () => req('GET', '/api/weekly-objectives');
export const createObjective = (data) => req('POST', '/api/weekly-objectives', data);
export const updateObjective = (id, data) => req('PUT', `/api/weekly-objectives/${id}`, data);
export const deleteObjective = (id) => req('DELETE', `/api/weekly-objectives/${id}`);

// ── Channels ───────────────────────────────────────────────────────────────────
export const getChannels = () => req('GET', '/api/channels');
export const createChannel = (data) => req('POST', '/api/channels', data);
export const updateChannel = (id, data) => req('PUT', `/api/channels/${id}`, data);
export const deleteChannel = (id) => req('DELETE', `/api/channels/${id}`);

// ── Focus ──────────────────────────────────────────────────────────────────────
export const startSession = (data) => req('POST', '/api/focus/start', data);
export const stopSession = (data) => req('POST', '/api/focus/stop', data);
export const getActiveSession = () => req('GET', '/api/focus/active');
export const getRecommendation = () => req('GET', '/api/focus/recommend');
export const getTodayStats = () => req('GET', '/api/focus/today');
export const getFocusTasks = () => req('GET', '/api/focus/tasks');
export const getSessionHistory = () => req('GET', '/api/focus/history');

// ── Rituals & Daily Highlights ─────────────────────────────────────────────────
export const generateShutdown = (data = {}) => req('POST', '/api/rituals/shutdown', data);
export const getHighlights = (limit = 30, type = null) => {
  const params = new URLSearchParams({ limit });
  if (type) params.set('highlight_type', type);
  return req('GET', `/api/rituals/highlights?${params}`);
};
export const getHighlightByDate = (date) => req('GET', `/api/rituals/highlights/${date}`);
export const createHighlight = (data) => req('POST', '/api/rituals/highlights', data);
export const deleteHighlight = (id) => req('DELETE', `/api/rituals/highlights/${id}`);

// Legacy alias
export const getReminders = () => req('GET', '/api/reminders');
export const recordAction = (id, action) => req('POST', `/api/reminders/${id}/action`, { action });

// ── Calendar ───────────────────────────────────────────────────────────────────
export const getCalendarEvents = (days = 4, timeMin = null, timeMax = null) => {
  let url = `/api/calendar/events?days=${days}`;
  if (timeMin && timeMax) {
    url += `&time_min=${encodeURIComponent(timeMin)}&time_max=${encodeURIComponent(timeMax)}`;
  }
  return req('GET', url);
};

// ── Analytics ──────────────────────────────────────────────────────────────────
export const getFullReport = () => req('GET', '/api/analytics/report');

// ── Health Check ───────────────────────────────────────────────────────────────
export const healthCheck = () => req('GET', '/health');

// ── Generic API Client ─────────────────────────────────────────────────────────
const api = {
  get: (path) => req('GET', path),
  post: (path, body) => req('POST', path, body),
  patch: (path, body) => req('PATCH', path, body),
  put: (path, body) => req('PUT', path, body),
  delete: (path) => req('DELETE', path),
};
export default api;
