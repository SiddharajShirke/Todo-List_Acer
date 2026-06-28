/**
 * api.js — Centralised API client
 * - Base URL from VITE_API_URL env var
 * - JWT stored in localStorage so it survives page refresh
 * - All API functions exported for use across pages
 */

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TOKEN_KEY = "auth_token";

// ── Token helpers ──────────────────────────────────────────────────
export const setToken = (t) => {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
};
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

// ── Core request helper ────────────────────────────────────────────
async function req(method, path, body) {
  const token = getToken();
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

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

// ── Auth ───────────────────────────────────────────────────────────
export const demoLogin = () => req("POST", "/auth/demo-login");
export const getMe = () => req("GET", "/auth/me");
export const updatePreferences = (preferences) => req("PATCH", "/auth/me/preferences", { preferences });
export const logout = () => clearToken();

// ── Commitments ────────────────────────────────────────────────────
export const ingestCommitment = (rawText, source = "manual") =>
  req("POST", "/api/commitments/ingest", { raw_text: rawText, source });
export const createManual = (data) => req("POST", "/api/commitments/manual", data);
export const getCommitments = () => req("GET", "/api/commitments");
export const getCommitment = (id) => req("GET", `/api/commitments/${id}`);
export const markDone = (id) => req("PATCH", `/api/commitments/${id}/done`);
export const deleteCommitment = (id) => req("DELETE", `/api/commitments/${id}`);

// ── Tasks ──────────────────────────────────────────────────────────
export const getTasks = (plannedDate) => req("GET", `/api/tasks${plannedDate ? '?planned_date=' + plannedDate : ''}`);
export const markTaskDone = (taskId) => req("PATCH", `/api/tasks/${taskId}/done`);
export const getRecoveryPlan = (commitmentId) => req("GET", `/api/tasks/${commitmentId}/recovery-plan`);

// ── Focus ──────────────────────────────────────────────────────────
export const startSession = (data) => req("POST", "/api/focus/start", data);
export const stopSession = (data) => req("POST", "/api/focus/stop", data);
export const getActiveSession = () => req("GET", "/api/focus/active");
export const getRecommendation = () => req("GET", "/api/focus/recommend");
export const getTodayStats = () => req("GET", "/api/focus/today");
export const getFocusTasks = () => req("GET", "/api/focus/tasks");
export const getSessionHistory = () => req("GET", "/api/focus/history");

// ── Reminders & Calendar ───────────────────────────────────────────
export const getReminders = () => req("GET", "/api/reminders");
export const recordAction = (id, action) => req("POST", `/api/reminders/${id}/action`, { action });
export const getCalendarEvents = (days = 4, timeMin = null, timeMax = null) => {
  let url = `/api/calendar/events?days=${days}`;
  if (timeMin && timeMax) {
    url += `&time_min=${encodeURIComponent(timeMin)}&time_max=${encodeURIComponent(timeMax)}`;
  }
  return req("GET", url);
};

// ── Analytics ──────────────────────────────────────────────────────
export const getFullReport = () => req("GET", "/api/analytics/report");

// ── Generic API Client ─────────────────────────────────────────────
const api = {
  get: (path) => req("GET", path),
  post: (path, body) => req("POST", path, body),
  patch: (path, body) => req("PATCH", path, body),
  delete: (path) => req("DELETE", path),
};
export default api;
