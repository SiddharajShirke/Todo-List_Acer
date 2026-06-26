const BASE_URL = "http://localhost:8000";

let _token = null;

export const setToken = (t) => { _token = t; };
export const getToken = () => _token;

async function req(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  if (_token) headers["Authorization"] = `Bearer ${_token}`;
  
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

// Auth
export const demoLogin = () => req("POST", "/auth/demo-login");
export const getMe = () => req("GET", "/auth/me");

// Commitments
export const ingestCommitment = (rawText, source = "manual") =>
  req("POST", "/api/commitments/ingest", { raw_text: rawText, source });
export const createManual = (data) => req("POST", "/api/commitments/manual", data);
export const getCommitments = () => req("GET", "/api/commitments");
export const getCommitment = (id) => req("GET", `/api/commitments/${id}`);
export const markDone = (id) => req("PATCH", `/api/commitments/${id}/done`);
export const deleteCommitment = (id) => req("DELETE", `/api/commitments/${id}`);

// Tasks
export const markTaskDone = (taskId) => req("PATCH", `/api/tasks/${taskId}/done`);
export const getRecoveryPlan = (commitmentId) => req("GET", `/api/tasks/${commitmentId}/recovery-plan`);

// Focus
export const startSession = (data) => req("POST", "/api/focus/start", data);
export const stopSession = (data) => req("POST", "/api/focus/stop", data);
export const getActiveSession = () => req("GET", "/api/focus/active");
export const getRecommendation = () => req("GET", "/api/focus/recommend");
export const getTodayStats = () => req("GET", "/api/focus/today");
export const getFocusTasks = () => req("GET", "/api/focus/tasks");

// Reminders
export const getReminders = () => req("GET", "/api/reminders");
export const recordAction = (id, action) => req("POST", `/api/reminders/${id}/action`, action);

// Analytics
export const getFullReport = () => req("GET", "/api/analytics/report");
