import { useState, useEffect, useCallback } from 'react';
import { getCommitments, ingestCommitment, createManual, markDone, deleteCommitment, createTask, aiPlan, aiRecover } from '../services/api';

// ── AI Result Panel (shown inline below commitment card) ──────────────────────
function AiResultPanel({ title, content, commitmentId, onClose }) {
  const [dismissed, setDismissed] = useState([]);
  const [added, setAdded]         = useState([]);
  const [adding, setAdding]       = useState(null);

  const lines = content
    .split('\n')
    .map(l => l.replace(/^[\d\-\*\.\s•]+/, '').trim())
    .filter(l => l.length > 5);

  const handleAddTask = async (line, idx) => {
    setAdding(idx);
    try {
      await createTask({ title: line, commitment_id: commitmentId, priority: 'medium' });
      setAdded(prev => [...prev, idx]);
    } catch (e) { console.error('Failed to create task:', e); }
    finally { setAdding(null); }
  };

  const handleAddAll = async () => {
    for (let i = 0; i < lines.length; i++) {
      if (!added.includes(i) && !dismissed.includes(i)) await handleAddTask(lines[i], i);
    }
  };

  const pending = lines.filter((_, i) => !added.includes(i) && !dismissed.includes(i));

  return (
    <div className="ai-result-panel">
      <div className="ai-result-header">
        <span style={{ fontWeight: 600 }}>{title}</span>
        <button className="modal-close" onClick={onClose}>✕</button>
      </div>
      <div className="ai-result-cards">
        {lines.map((line, i) => {
          if (dismissed.includes(i)) return null;
          const isAdded = added.includes(i);
          return (
            <div key={i} className={`ai-task-card ${isAdded ? 'task-added' : ''}`}>
              <span className="ai-task-icon">📌</span>
              <span className="ai-task-text">{line}</span>
              <div className="ai-task-actions">
                {isAdded ? (
                  <span className="task-added-badge">✅ Added</span>
                ) : (
                  <>
                    <button className="btn btn-primary btn-xs" disabled={adding === i} onClick={() => handleAddTask(line, i)}>
                      {adding === i ? '…' : '+ Task'}
                    </button>
                    <button className="btn btn-ghost btn-xs" onClick={() => setDismissed(p => [...p, i])}>✕</button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {pending.length > 0 && (
        <button className="btn btn-primary" style={{ marginTop: 12, width: '100%' }} onClick={handleAddAll}>
          ✅ Accept All {pending.length} Steps as Tasks
        </button>
      )}
    </div>
  );
}

function RiskBadge({ score }) {
  const level = score >= 0.7 ? 'high' : score >= 0.4 ? 'medium' : 'low';
  return <span className={`risk-badge risk-${level}`}>{level === 'high' ? '🔴 High' : level === 'medium' ? '🟡 Med' : '🟢 Low'}</span>;
}

function TypeIcon({ type }) {
  const icons = { task: '📋', bill: '💳', meeting: '🤝', deadline: '⏰', other: '📌' };
  return <span title={type}>{icons[type] || '📌'}</span>;
}

function Commitments() {
  const [items, setItems]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [tab, setTab]           = useState('list');   // 'list' | 'ai' | 'manual'
  const [search, setSearch]     = useState('');
  const [filter, setFilter]     = useState('all');    // all | high | overdue

  // AI ingest state
  const [rawText, setRawText]   = useState('');
  const [ingesting, setIngesting] = useState(false);
  const [ingestErr, setIngestErr] = useState(null);

  // Manual form state
  const today = new Date().toISOString().split('T')[0];
  const [form, setForm]         = useState({ title: '', type: 'task', description: '', due_date: today });
  const [saving, setSaving]     = useState(false);
  const [saveErr, setSaveErr]   = useState(null);

  // AI panel state
  const [aiPanel, setAiPanel]     = useState(null); // { commitmentId, title, content }
  const [aiLoading, setAiLoading] = useState(null); // commitmentId currently loading

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getCommitments();
      setItems(data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Sync with AI Agent actions
  useEffect(() => {
    const handleAiSync = () => {
      console.log('AI action completed, syncing Commitments...');
      load();
    };
    window.addEventListener('ai_action_completed', handleAiSync);
    return () => window.removeEventListener('ai_action_completed', handleAiSync);
  }, [load]);

  // ── Filters ─────────────────────────────────────────────────────
  const filtered = items.filter(c => {
    const matchSearch = c.title.toLowerCase().includes(search.toLowerCase());
    if (!matchSearch) return false;
    if (filter === 'high') return c.risk_score >= 0.7;
    if (filter === 'overdue') return c.days_until_due !== null && c.days_until_due < 0;
    return true;
  });

  // ── Actions ──────────────────────────────────────────────────────
  const handleDone = async (id) => {
    try { await markDone(id); setItems(cs => cs.filter(c => c.id !== id)); }
    catch (e) { console.error(e); }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this commitment?')) return;
    try { await deleteCommitment(id); setItems(cs => cs.filter(c => c.id !== id)); }
    catch (e) { console.error(e); }
  };

  const handleAiPlan = async (c) => {
    setAiLoading(c.id); setAiPanel(null);
    try {
      const result = await aiPlan(c.id);
      setAiPanel({ commitmentId: c.id, title: `📋 Execution Plan: ${c.title}`, content: result.response });
    } catch (e) { alert('AI Plan error: ' + e.message); }
    finally { setAiLoading(null); }
  };

  const handleAiRecover = async (c) => {
    setAiLoading(c.id); setAiPanel(null);
    try {
      const result = await aiRecover(c.id);
      setAiPanel({ commitmentId: c.id, title: `🔄 Recovery Plan: ${c.title}`, content: result.response });
    } catch (e) { alert('AI Recovery error: ' + e.message); }
    finally { setAiLoading(null); }
  };

  // ── AI Ingest ────────────────────────────────────────────────────
  const handleIngest = async (e) => {
    e.preventDefault();
    if (!rawText.trim()) return;
    setIngesting(true); setIngestErr(null);
    try {
      const c = await ingestCommitment(rawText);
      setItems(cs => [c, ...cs]);
      setRawText('');
      setTab('list');
    } catch (e) { setIngestErr(e.message); }
    finally { setIngesting(false); }
  };

  // ── Manual Create ─────────────────────────────────────────────────
  const setF = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const handleManual = async (e) => {
    e.preventDefault();
    setSaving(true); setSaveErr(null);
    try {
      const c = await createManual(form);
      setItems(cs => [c, ...cs]);
      setForm({ title: '', type: 'task', description: '', due_date: today });
      setTab('list');
    } catch (e) { setSaveErr(e.message); }
    finally { setSaving(false); }
  };

  const formatDue = (days) => {
    if (days === null || days === undefined) return <span className="muted">No due date</span>;
    if (days < 0) return <span style={{ color: 'var(--color-danger)', fontWeight: 600 }}>⚠ Overdue {Math.abs(days)}d</span>;
    if (days === 0) return <span style={{ color: 'var(--color-warning)', fontWeight: 600 }}>Due today!</span>;
    return <span className="muted">in {days}d</span>;
  };

  return (
    <div className="tab-content">
      <header className="top-header">
        <h2>Commitments</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className={`btn ${tab === 'ai' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setTab(tab === 'ai' ? 'list' : 'ai')}>
            🤖 AI Ingest
          </button>
          <button className={`btn ${tab === 'manual' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setTab(tab === 'manual' ? 'list' : 'manual')}>
            ✏️ Add Manual
          </button>
        </div>
      </header>

      {/* ── AI Ingest Panel ── */}
      {tab === 'ai' && (
        <div className="panel">
          <h3>🤖 AI Commitment Extraction</h3>
          <p className="muted">Paste any text — email, message, note — and AI will extract the commitment details.</p>
          <form onSubmit={handleIngest}>
            <textarea
              className="ai-input"
              rows={5}
              value={rawText}
              onChange={e => setRawText(e.target.value)}
              placeholder='e.g. "Hey, can you submit the Q3 report by next Friday? Also, the rent is due on the 30th."'
            />
            {ingestErr && <div className="error-banner">⚠️ {ingestErr}</div>}
            <button type="submit" className="btn btn-primary" disabled={ingesting || !rawText.trim()}>
              {ingesting ? '🤖 Extracting…' : '🚀 Extract & Save to Supabase'}
            </button>
          </form>
        </div>
      )}

      {/* ── Manual Add Panel ── */}
      {tab === 'manual' && (
        <div className="panel">
          <h3>✏️ Add Commitment Manually</h3>
          <form onSubmit={handleManual} className="modal-form">
            <label>Title *
              <input required value={form.title} onChange={e => setF('title', e.target.value)} placeholder="What needs to be done?" />
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <label>Type
                <select value={form.type} onChange={e => setF('type', e.target.value)}>
                  <option value="task">Task</option>
                  <option value="bill">Bill / Payment</option>
                  <option value="meeting">Meeting</option>
                  <option value="deadline">Deadline</option>
                  <option value="other">Other</option>
                </select>
              </label>
              <label>Due Date *
                <input type="date" required value={form.due_date} onChange={e => setF('due_date', e.target.value)} />
              </label>
            </div>
            <label>Description
              <textarea rows={3} value={form.description} onChange={e => setF('description', e.target.value)} placeholder="Optional details…" />
            </label>
            {saveErr && <div className="error-banner">⚠️ {saveErr}</div>}
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : '💾 Save to Supabase'}
            </button>
          </form>
        </div>
      )}

      {/* ── List View ── */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          className="search-input"
          placeholder="🔍 Search commitments…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <div className="filter-tabs">
          {['all', 'high', 'overdue'].map(f => (
            <button key={f} className={`filter-btn ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>
              {f === 'all' ? 'All' : f === 'high' ? '🔴 High Risk' : '⚠️ Overdue'}
            </button>
          ))}
        </div>
        <span className="muted">{filtered.length} item{filtered.length !== 1 ? 's' : ''}</span>
      </div>

      {loading ? (
        <div className="skeleton-list">{[1,2,3,4].map(i => <div key={i} className="skeleton-item tall" />)}</div>
      ) : filtered.length === 0 ? (
        <div className="empty-state large">
          <span>📭</span>
          <p>{search ? 'No results found.' : 'No active commitments. Add one above!'}</p>
        </div>
      ) : (
        <div className="commitments-grid">
          {filtered.map(c => (
            <div key={c.id} className="commitment-card">
              <div className="commitment-card-header">
                <TypeIcon type={c.type} />
                <span className="commitment-card-title">{c.title}</span>
                <RiskBadge score={c.risk_score} />
              </div>
              {c.description && <p className="commitment-card-desc muted">{c.description}</p>}
              <div className="commitment-card-footer">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className="muted" style={{ fontSize: '0.75rem' }}>Priority</span>
                    <div className="priority-bar-wrap" style={{ width: 80 }}>
                      <div className="priority-bar" style={{ width: `${Math.min(c.priority_score || 0, 100)}%` }} />
                    </div>
                    <span className="muted" style={{ fontSize: '0.75rem' }}>{Math.round(c.priority_score || 0)}</span>
                  </div>
                  <div>{formatDue(c.days_until_due)}</div>
                </div>
                <div className="commitment-card-actions">
                  <button
                    className="btn btn-ghost btn-sm"
                    disabled={aiLoading === c.id}
                    onClick={() => handleAiPlan(c)}
                    title="Generate execution plan"
                  >
                    {aiLoading === c.id ? '⏳' : '🤖 Plan'}
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    disabled={aiLoading === c.id}
                    onClick={() => handleAiRecover(c)}
                    title="Generate recovery plan"
                  >
                    {aiLoading === c.id ? '⏳' : '🔄 Recover'}
                  </button>
                  <button className="btn btn-ghost btn-sm" onClick={() => handleDone(c.id)} title="Mark done">✓ Done</button>
                  <button className="btn btn-ghost btn-sm danger" onClick={() => handleDelete(c.id)} title="Delete">🗑</button>
                </div>
              </div>
              {aiPanel && aiPanel.commitmentId === c.id && (
                <AiResultPanel
                  title={aiPanel.title}
                  content={aiPanel.content}
                  commitmentId={c.id}
                  onClose={() => setAiPanel(null)}
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Commitments;
