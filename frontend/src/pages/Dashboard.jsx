import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { getTodayStats, getCommitments, getReminders, createManual, markDone, deleteCommitment } from '../services/api';

// ── Small reusable components ──────────────────────────────────────
function StatCard({ icon, label, value, sub }) {
  return (
    <div className="stat-card">
      <div className="stat-icon">{icon}</div>
      <h3>{label}</h3>
      <div className="stat-value">{value ?? '—'}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

function RiskBadge({ score }) {
  const level = score >= 0.7 ? 'high' : score >= 0.4 ? 'medium' : 'low';
  const labels = { high: '🔴 High', medium: '🟡 Med', low: '🟢 Low' };
  return <span className={`risk-badge risk-${level}`}>{labels[level]}</span>;
}

function PriorityBar({ score }) {
  const pct = Math.round((score || 0) * 100) / 100;
  return (
    <div className="priority-bar-wrap" title={`Priority: ${pct}`}>
      <div className="priority-bar" style={{ width: `${Math.min(pct, 100)}%` }} />
    </div>
  );
}

// ── Add Commitment Modal ───────────────────────────────────────────
function AddCommitmentModal({ onClose, onAdded }) {
  const today = new Date().toISOString().split('T')[0];
  const [form, setForm] = useState({ title: '', type: 'task', description: '', due_date: today });
  const [saving, setSaving] = useState(false);
  const [err, setErr]       = useState(null);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true); setErr(null);
    try {
      const created = await createManual(form);
      onAdded(created);
      onClose();
    } catch (e) {
      setErr(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>➕ Add Commitment</h3>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-form">
          <label>Title *
            <input required value={form.title} onChange={e => set('title', e.target.value)} placeholder="e.g. Submit project report" />
          </label>
          <label>Type
            <select value={form.type} onChange={e => set('type', e.target.value)}>
              <option value="task">Task</option>
              <option value="bill">Bill / Payment</option>
              <option value="meeting">Meeting</option>
              <option value="deadline">Deadline</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label>Due Date *
            <input type="date" required value={form.due_date} onChange={e => set('due_date', e.target.value)} />
          </label>
          <label>Description
            <textarea rows={3} value={form.description} onChange={e => set('description', e.target.value)} placeholder="Optional details…" />
          </label>
          {err && <div className="error-banner">⚠️ {err}</div>}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save to Supabase'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────
function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats]         = useState(null);
  const [commitments, setCommitments] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [showModal, setShowModal] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, c, r] = await Promise.all([getTodayStats(), getCommitments(), getReminders()]);
      setStats(s);
      setCommitments(c.slice(0, 5));
      setReminders(r.slice(0, 5));
    } catch (e) {
      console.error('Dashboard load error:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Sync with AI Agent actions
  useEffect(() => {
    const handleAiSync = () => {
      console.log('AI action completed, syncing Dashboard...');
      load();
    };
    window.addEventListener('ai_action_completed', handleAiSync);
    return () => window.removeEventListener('ai_action_completed', handleAiSync);
  }, [load]);

  const handleMarkDone = async (id) => {
    try {
      await markDone(id);
      setCommitments(cs => cs.filter(c => c.id !== id));
    } catch (e) { console.error(e); }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this commitment?')) return;
    try {
      await deleteCommitment(id);
      setCommitments(cs => cs.filter(c => c.id !== id));
    } catch (e) { console.error(e); }
  };

  const handleAdded = (c) => setCommitments(cs => [c, ...cs].slice(0, 5));

  const formatDue = (days) => {
    if (days === null || days === undefined) return '';
    if (days < 0) return <span style={{ color: 'var(--color-danger)' }}>Overdue {Math.abs(days)}d</span>;
    if (days === 0) return <span style={{ color: 'var(--color-warning)' }}>Due today</span>;
    return <span className="muted">in {days}d</span>;
  };

  return (
    <div id="dashboard-tab" className="tab-content">
      <header className="top-header">
        <div>
          <h2>Dashboard</h2>
          {user && <p className="muted" style={{ margin: 0 }}>Welcome back, {user.name || user.email} 👋</p>}
        </div>
        <button id="add-commitment-btn" className="btn btn-primary" onClick={() => setShowModal(true)}>
          + Add Commitment
        </button>
      </header>

      {/* Stats */}
      <div className="stats-grid">
        <StatCard icon="🕐" label="Focus Hours"  value={loading ? '…' : stats?.total_hours ?? 0}       sub="today" />
        <StatCard icon="🍅" label="Pomodoros"    value={loading ? '…' : stats?.pomodoros_completed ?? 0} sub="today" />
        <StatCard icon="🔥" label="Streak"       value={loading ? '…' : `${stats?.streak_days ?? 0}d`}   sub="current" />
        <StatCard icon="✅" label="Sessions"     value={loading ? '…' : stats?.sessions_count ?? 0}      sub="today" />
      </div>

      <div className="dashboard-grid">
        {/* Top Commitments */}
        <div className="commitments-section">
          <h3>Top Commitments</h3>
          <div className="list-container">
            {loading ? (
              <div className="skeleton-list">{[1,2,3].map(i => <div key={i} className="skeleton-item" />)}</div>
            ) : commitments.length === 0 ? (
              <div className="empty-state">
                <span>📭</span>
                <p>No active commitments. Add one to get started!</p>
              </div>
            ) : (
              <ul className="commitment-list">
                {commitments.map(c => (
                  <li key={c.id} className="commitment-item">
                    <div className="commitment-main">
                      <span className="commitment-title">{c.title}</span>
                      <div className="commitment-meta">
                        <span className="type-badge">{c.type}</span>
                        <RiskBadge score={c.risk_score} />
                        <span>{formatDue(c.days_until_due)}</span>
                      </div>
                      <PriorityBar score={c.priority_score} />
                    </div>
                    <div className="commitment-actions">
                      <button className="icon-btn" title="Mark done" onClick={() => handleMarkDone(c.id)}>✓</button>
                      <button className="icon-btn danger" title="Delete" onClick={() => handleDelete(c.id)}>🗑</button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Recent Reminders */}
        <div className="reminders-section">
          <h3>Recent Reminders</h3>
          <div className="list-container">
            {loading ? (
              <div className="skeleton-list">{[1,2].map(i => <div key={i} className="skeleton-item" />)}</div>
            ) : reminders.length === 0 ? (
              <div className="empty-state">
                <span>🔔</span>
                <p>No reminders yet.</p>
              </div>
            ) : (
              <ul className="reminder-list">
                {reminders.map(r => (
                  <li key={r.id} className="reminder-item">
                    <span className="reminder-style-dot" data-style={r.style} />
                    <div>
                      <p className="reminder-message">{r.message}</p>
                      <span className="muted" style={{ fontSize: '0.75rem' }}>
                        {r.sent_at ? new Date(r.sent_at).toLocaleString() : ''}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {showModal && <AddCommitmentModal onClose={() => setShowModal(false)} onAdded={handleAdded} />}
    </div>
  );
}

export default Dashboard;
