import { useState, useEffect, useRef, useCallback } from 'react';
import {
  startSession, stopSession, getActiveSession,
  getRecommendation, getFocusTasks, getSessionHistory,
  updatePreferences, getMe
} from '../services/api';
import { useStats } from '../context/StatsContext';

// ─────────────────────────────────────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────────────────────────────────────
const MODES = {
  pomodoro:  { label: 'Pomodoro',   icon: '🍅', default: 25, isBreak: false, prefKey: 'pomodoro_work_mins' },
  deepwork:  { label: 'Deep Work',  icon: '🧠', default: 90, isBreak: false, prefKey: 'deepwork_block_mins' },
  break:     { label: 'Break',      icon: '☕', default: 5,  isBreak: true,  prefKey: 'pomodoro_break_mins' },
  longbreak: { label: 'Long Break', icon: '🛋', default: 20, isBreak: true,  prefKey: 'pomodoro_long_break_mins' },
};

const pad = n => String(n).padStart(2, '0');

// ─────────────────────────────────────────────────────────────────────────────
// Timer ring radius
// ─────────────────────────────────────────────────────────────────────────────
const R = 108;
const CIRC = 2 * Math.PI * R;

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────
export default function Focus() {
  const { refreshStats } = useStats();

  // ── Timer state ───────────────────────────────────────────────────
  const [mode, setMode]         = useState('pomodoro');
  const [durations, setDurations] = useState({ pomodoro: 25, deepwork: 90, break: 5, longbreak: 20 });
  const [timeLeft, setTimeLeft] = useState(25 * 60);
  const [running, setRunning]   = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [pomNumber, setPomNumber] = useState(1);

  // ── Edit timers panel ─────────────────────────────────────────────
  const [editOpen, setEditOpen] = useState(false);
  const [editVals, setEditVals] = useState({ pomodoro: 25, deepwork: 90, break: 5, longbreak: 20 });

  // ── Data ──────────────────────────────────────────────────────────
  const [tasks, setTasks]           = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [history, setHistory]       = useState([]);

  // ── Status ────────────────────────────────────────────────────────
  const [status, setStatus]   = useState('');
  const [loading, setLoading] = useState(false);

  const intervalRef = useRef(null);
  const totalRef    = useRef(25 * 60);

  // ── Helpers ───────────────────────────────────────────────────────
  const stopTick = () => { clearInterval(intervalRef.current); intervalRef.current = null; };

  const startTick = (seconds) => {
    stopTick();
    setTimeLeft(seconds);
    intervalRef.current = setInterval(() => {
      setTimeLeft(t => {
        if (t <= 1) {
          stopTick();
          setRunning(false);
          setStatus('⏰ Session complete! Well done!');
          return 0;
        }
        return t - 1;
      });
    }, 1000);
  };

  const loadData = useCallback(async () => {
    try {
      const [t, rec, hist, me] = await Promise.all([
        getFocusTasks(), getRecommendation(), getSessionHistory(), getMe()
      ]);
      setTasks(t);
      setRecommendation(rec.recommendation);
      setHistory(hist);
      if (me.preferences) {
        const prefs = me.preferences;
        const next = {
          pomodoro:  prefs.pomodoro_work_mins      || 25,
          deepwork:  prefs.deepwork_block_mins      || 90,
          break:     prefs.pomodoro_break_mins      || 5,
          longbreak: prefs.pomodoro_long_break_mins || 20,
        };
        setDurations(next);
        setEditVals(next);
      }
      return t;
    } catch (e) {
      console.error('Focus load error:', e);
      return [];
    }
  }, []);

  // ── On mount: check for active session ────────────────────────────
  useEffect(() => {
    const init = async () => {
      const freshTasks = await loadData();
      try {
        const { session } = await getActiveSession();
        if (session) {
          const elapsed   = Math.floor((Date.now() - new Date(session.started_at + 'Z').getTime()) / 1000);
          const planned   = session.planned_duration_minutes * 60;
          const remaining = Math.max(0, planned - elapsed);
          const m = session.mode || 'pomodoro';
          setMode(m);
          setSessionId(session.id);
          setRunning(true);
          setPomNumber(session.pomodoro_number);
          totalRef.current = planned;
          if (session.task_id) {
            const t = freshTasks.find(x => x.id === session.task_id);
            if (t) setSelectedTask(t);
          }
          startTick(remaining);
          setStatus('▶ Resuming active session…');
        }
      } catch (_) { /* no active session */ }
    };
    init();
    return () => stopTick();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Sync timeLeft total when mode / durations change (not running) ─
  useEffect(() => {
    if (!running) {
      const secs = durations[mode] * 60;
      setTimeLeft(secs);
      totalRef.current = secs;
    }
  }, [mode, durations, running]);

  // ── Session number when task changes ──────────────────────────────
  useEffect(() => {
    if (!running) {
      setPomNumber((selectedTask?.pomodoros_completed ?? 0) + 1);
    }
  }, [selectedTask, running]);

  // ── Start ─────────────────────────────────────────────────────────
  const handleStart = async () => {
    setLoading(true);
    setStatus('');
    try {
      const mins = durations[mode];
      const sess = await startSession({
        mode,
        task_id: selectedTask?.id ?? null,
        planned_duration_minutes: mins,
        pomodoro_number: pomNumber,
        is_break: MODES[mode].isBreak,
      });
      setSessionId(sess.id);
      totalRef.current = mins * 60;
      setRunning(true);
      startTick(mins * 60);
      setStatus(`▶ ${MODES[mode].icon} ${MODES[mode].label} started!`);
    } catch (e) {
      setStatus('⚠ Failed to start: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Stop ──────────────────────────────────────────────────────────
  const handleStop = async (stopStatus = 'completed') => {
    stopTick();
    setRunning(false);
    setLoading(true);
    try {
      if (sessionId) {
        const res = await stopSession({ session_id: sessionId, status: stopStatus, flow_rating: null });
        setStatus(
          stopStatus === 'completed'
            ? `✅ Saved! ${res.duration_minutes}m recorded${selectedTask ? ' to task' : ''}.`
            : '⏸ Interrupted and saved.'
        );
      }
      setSessionId(null);
      // Reset timer
      const secs = durations[mode] * 60;
      setTimeLeft(secs);
      totalRef.current = secs;
      refreshStats();
      const freshTasks = await loadData();
      if (selectedTask) {
        const updated = freshTasks.find(t => t.id === selectedTask.id);
        if (updated) setSelectedTask(updated);
      }
    } catch (e) {
      setStatus('⚠ Failed to save: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Save defaults ─────────────────────────────────────────────────
  const handleSaveDefaults = async () => {
    const toSave = { ...editVals };
    setDurations(toSave);
    setEditVals(toSave);
    setEditOpen(false);
    try {
      await updatePreferences({
        pomodoro_work_mins: toSave.pomodoro,
        deepwork_block_mins: toSave.deepwork,
        pomodoro_break_mins: toSave.break,
        pomodoro_long_break_mins: toSave.longbreak,
      });
      setStatus('✅ Timer defaults saved!');
    } catch (e) {
      setStatus('⚠ Could not save defaults: ' + e.message);
    }
  };

  // ── SVG progress ──────────────────────────────────────────────────
  const pct    = totalRef.current > 0 ? ((totalRef.current - timeLeft) / totalRef.current) : 0;
  const offset = CIRC - pct * CIRC;
  const mins   = Math.floor(timeLeft / 60);
  const secs   = timeLeft % 60;

  return (
    <div className="focus-page" style={{ display: 'flex', gap: 24, height: '100%', minHeight: 0 }}>

      {/* ── Left column: Timer ──────────────────────────────────────── */}
      <div className="focus-left" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* Mode tabs */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          {Object.entries(MODES).map(([key, cfg]) => (
            <button
              key={key}
              onClick={() => !running && setMode(key)}
              disabled={running}
              style={{
                padding: '6px 14px', borderRadius: 20, border: 'none', cursor: running ? 'not-allowed' : 'pointer',
                background: mode === key ? 'var(--color-primary)' : 'var(--color-surface-2)',
                color: mode === key ? '#fff' : 'var(--color-text-muted)',
                fontWeight: mode === key ? 600 : 400, fontSize: '0.85rem', transition: 'all 0.2s',
              }}
            >
              {cfg.icon} {cfg.label}
            </button>
          ))}
          {!running && (
            <button
              onClick={() => { setEditOpen(o => !o); setEditVals(durations); }}
              title="Edit timer durations"
              style={{ background: 'none', border: '1px solid var(--color-surface-2)', borderRadius: 20, padding: '4px 10px', cursor: 'pointer', color: 'var(--color-text-muted)', fontSize: '0.8rem' }}
            >
              ⚙️ Edit
            </button>
          )}
        </div>

        {/* Edit timers panel */}
        {editOpen && !running && (
          <div style={{ background: 'var(--color-surface-1)', borderRadius: 10, padding: 16, display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            {Object.entries(MODES).map(([key, cfg]) => (
              <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <label style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{cfg.icon} {cfg.label} (min)</label>
                <input
                  type="number" min="1" max="240"
                  value={editVals[key]}
                  onChange={e => setEditVals(v => ({ ...v, [key]: Number(e.target.value) }))}
                  style={{ width: 68, padding: '4px 8px', borderRadius: 6, border: '1px solid var(--color-surface-2)', background: 'var(--color-surface)', color: 'var(--color-text)' }}
                />
              </div>
            ))}
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => { setDurations({ ...editVals }); setEditOpen(false); }}
                style={{ padding: '6px 14px', borderRadius: 8, border: 'none', background: 'var(--color-surface-3)', cursor: 'pointer', color: 'var(--color-text)', fontSize: '0.85rem' }}
              >
                Apply once
              </button>
              <button
                onClick={handleSaveDefaults}
                style={{ padding: '6px 14px', borderRadius: 8, border: 'none', background: 'var(--color-primary)', cursor: 'pointer', color: '#fff', fontWeight: 600, fontSize: '0.85rem' }}
              >
                💾 Save as Default
              </button>
            </div>
          </div>
        )}

        {/* Circular timer */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20 }}>
          <svg width={260} height={260} style={{ overflow: 'visible' }}>
            {/* Track */}
            <circle cx={130} cy={130} r={R} fill="none" stroke="var(--color-surface-2)" strokeWidth={12} />
            {/* Progress */}
            <circle
              cx={130} cy={130} r={R}
              fill="none"
              stroke={running ? 'var(--color-primary)' : 'var(--color-surface-3)'}
              strokeWidth={12}
              strokeDasharray={CIRC}
              strokeDashoffset={offset}
              strokeLinecap="round"
              transform="rotate(-90 130 130)"
              style={{ transition: running ? 'stroke-dashoffset 1s linear' : 'none' }}
            />
            {/* Mode */}
            <text x={130} y={112} textAnchor="middle" style={{ fontSize: 14, fill: 'var(--color-text-muted)', fontFamily: 'inherit' }}>
              {MODES[mode].icon} {MODES[mode].label}
            </text>
            {/* Time */}
            <text x={130} y={146} textAnchor="middle" style={{ fontSize: 38, fontWeight: 700, fill: 'var(--color-text)', fontFamily: 'inherit', fontVariantNumeric: 'tabular-nums' }}>
              {pad(mins)}:{pad(secs)}
            </text>
            {/* Session # */}
            <text x={130} y={168} textAnchor="middle" style={{ fontSize: 12, fill: 'var(--color-text-muted)', fontFamily: 'inherit' }}>
              Session #{pomNumber}
            </text>
          </svg>

          {/* Controls */}
          {!running ? (
            <button
              id="focus-start-btn"
              onClick={handleStart}
              disabled={loading}
              style={{
                padding: '12px 40px', borderRadius: 30, border: 'none',
                background: 'var(--color-primary)', color: '#fff',
                fontSize: '1rem', fontWeight: 700, cursor: 'pointer',
                boxShadow: '0 4px 16px rgba(0,0,0,0.3)', transition: 'transform 0.1s',
                opacity: loading ? 0.6 : 1,
              }}
            >
              {loading ? '…' : '▶ Start Session'}
            </button>
          ) : (
            <div style={{ display: 'flex', gap: 12 }}>
              <button
                onClick={() => handleStop('completed')}
                disabled={loading}
                style={{ padding: '10px 28px', borderRadius: 24, border: 'none', background: '#22c55e', color: '#fff', fontWeight: 700, cursor: 'pointer', opacity: loading ? 0.6 : 1 }}
              >
                {loading ? '…' : '✅ Complete'}
              </button>
              <button
                onClick={() => handleStop('interrupted')}
                disabled={loading}
                style={{ padding: '10px 22px', borderRadius: 24, border: '1px solid var(--color-surface-2)', background: 'var(--color-surface-1)', color: 'var(--color-text-muted)', cursor: 'pointer', opacity: loading ? 0.6 : 1 }}
              >
                {loading ? '…' : '⏸ Interrupt'}
              </button>
            </div>
          )}

          {status && (
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--color-text-muted)', textAlign: 'center' }}>
              {status}
            </p>
          )}
        </div>

        {/* Today's session history */}
        <div style={{ background: 'var(--color-surface-1)', borderRadius: 10, padding: 16 }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9rem' }}>🕒 Today's Sessions</h4>
          {history.length === 0 ? (
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>No sessions completed yet today.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 160, overflowY: 'auto' }}>
              {history.map(h => (
                <div key={h.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', padding: '4px 0', borderBottom: '1px solid var(--color-surface-2)' }}>
                  <span>{MODES[h.mode]?.icon} {MODES[h.mode]?.label} #{h.pomodoro_number}</span>
                  <span style={{ color: 'var(--color-text-muted)' }}>{h.actual_duration_minutes}m</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Right column: Recommendation + Tasks ────────────────────── */}
      <div className="focus-right" style={{ width: 280, display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* AI recommendation */}
        {recommendation && (
          <div style={{ background: 'var(--color-surface-1)', borderRadius: 10, padding: 14, border: '1px solid var(--color-surface-2)' }}>
            <p style={{ margin: '0 0 6px 0', fontSize: '0.75rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>🤖 AI Recommends</p>
            <p style={{ margin: '0 0 4px 0', fontWeight: 600, fontSize: '0.9rem' }}>{recommendation.task_title}</p>
            <p style={{ margin: '0 0 8px 0', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>{recommendation.commitment_title}</p>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                🍅 {recommendation.pomodoros_completed}/{recommendation.pomodoros_estimated}
              </span>
              {!running && (
                <button
                  onClick={() => {
                    const t = tasks.find(x => x.id === recommendation.task_id);
                    if (t) setSelectedTask(t);
                  }}
                  style={{ padding: '4px 10px', borderRadius: 6, border: 'none', background: 'var(--color-primary)', color: '#fff', fontSize: '0.78rem', cursor: 'pointer' }}
                >
                  Focus →
                </button>
              )}
            </div>
          </div>
        )}

        {/* Task picker */}
        <div style={{ background: 'var(--color-surface-1)', borderRadius: 10, padding: 14, flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <h4 style={{ margin: 0, fontSize: '0.9rem' }}>📋 Today's Tasks</h4>
          {tasks.length === 0 ? (
            <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>No incomplete tasks for today. Add some in the Today page!</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto', maxHeight: 340 }}>
              {tasks.map(t => {
                const isSelected = selectedTask?.id === t.id;
                return (
                  <div
                    key={t.id}
                    onClick={() => !running && setSelectedTask(isSelected ? null : t)}
                    style={{
                      padding: '10px 12px', borderRadius: 8, cursor: running ? 'not-allowed' : 'pointer',
                      border: `1px solid ${isSelected ? 'var(--color-primary)' : 'var(--color-surface-2)'}`,
                      background: isSelected ? 'rgba(var(--color-primary-rgb, 99,102,241),0.12)' : 'var(--color-surface)',
                      transition: 'all 0.15s',
                      opacity: running && !isSelected ? 0.6 : 1,
                    }}
                  >
                    <p style={{ margin: '0 0 4px 0', fontSize: '0.84rem', fontWeight: 500 }}>{t.title}</p>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                      <span>{t.commitment_title}</span>
                      <span>🍅 {t.pomodoros_completed} | {Math.round((t.actual_minutes || 0) / 60 * 10) / 10}h</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {selectedTask && (
            <div style={{ marginTop: 'auto', padding: '8px 12px', borderRadius: 8, background: 'var(--color-primary)', color: '#fff', fontSize: '0.82rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>🎯 {selectedTask.title}</span>
              {!running && (
                <button
                  onClick={() => setSelectedTask(null)}
                  style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.7)', cursor: 'pointer', fontSize: '1rem', lineHeight: 1 }}
                >
                  ✕
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
