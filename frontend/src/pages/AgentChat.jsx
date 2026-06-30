/**
 * AgentChat.jsx — LangGraph AI Agent Chat Interface
 *
 * Architecture:
 *   - thread_id persisted in sessionStorage → Brain remembers conversation
 *   - Optimistic UI: user message appears instantly before API responds
 *   - tool_calls_made displayed as subtle "activity pills" under the AI response
 *   - Typing indicator shown while Brain is thinking (2-4s with tool calls)
 *   - New thread button clears sessionStorage and resets the conversation
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { aiChat } from '../services/api';

// ── Tool call label map ───────────────────────────────────────────────────────
const TOOL_LABELS = {
  fetch_tasks:           'Checked your tasks',
  fetch_commitments:     'Reviewed commitments',
  fetch_overdue_tasks:   'Scanned overdue items',
  fetch_daily_plan:      'Looked at your daily plan',
  fetch_focus_sessions:  'Checked focus sessions',
  fetch_productivity_stats: 'Reviewed productivity stats',
  create_task:           'Created a task',
  update_task_status:    'Updated task status',
  create_commitment:     'Created a commitment',
  set_daily_highlight:   'Saved daily highlight',
  create_reminder:       'Set a reminder',
  log_focus_session:     'Logged focus session',
  decompose_commitment:  'Broke down commitment into steps',
  generate_recovery_plan:'Built recovery plan',
  get_intervention_message: 'Crafted intervention message',
};

// ── Sub-components ────────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="chat-message assistant" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div className="chat-avatar">🤖</div>
      <div className="chat-bubble thinking">
        <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
      </div>
    </div>
  );
}

function ToolPills({ tools }) {
  if (!tools || tools.length === 0) return null;
  return (
    <div className="tool-pills">
      {tools.map((t, i) => (
        <span key={i} className="tool-pill">
          ⚡ {TOOL_LABELS[t] || t}
        </span>
      ))}
    </div>
  );
}

function ChatMessage({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`chat-message ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && <div className="chat-avatar">🤖</div>}
      <div className="chat-bubble-wrap">
        <div className={`chat-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
          {msg.content}
        </div>
        {!isUser && <ToolPills tools={msg.toolsUsed} />}
      </div>
      {isUser && <div className="chat-avatar user-avatar">👤</div>}
    </div>
  );
}

function SuggestedPrompts({ onSelect }) {
  const prompts = [
    "What tasks do I have today?",
    "Show me my high-risk commitments",
    "I'm falling behind on my goals — help me recover",
    "How many focus hours have I logged this week?",
    "Break down my most urgent commitment into steps",
    "What should I focus on right now?",
  ];
  return (
    <div className="suggested-prompts">
      <p className="muted" style={{ marginBottom: 12, fontSize: '0.85rem' }}>Try asking:</p>
      <div className="prompts-grid">
        {prompts.map((p, i) => (
          <button key={i} className="prompt-chip" onClick={() => onSelect(p)}>
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Main AgentChat Page ───────────────────────────────────────────────────────

const THREAD_KEY = 'ai_agent_thread_id';

export default function AgentChat() {
  const [messages, setMessages]       = useState([]);
  const [input, setInput]             = useState('');
  const [isThinking, setIsThinking]   = useState(false);
  const [error, setError]             = useState(null);
  const [threadId, setThreadId]       = useState(() => {
    return sessionStorage.getItem(THREAD_KEY) || crypto.randomUUID();
  });

  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  // Persist thread_id so Brain remembers across page navigations in same session
  useEffect(() => {
    sessionStorage.setItem(THREAD_KEY, threadId);
  }, [threadId]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const sendMessage = useCallback(async (text) => {
    const trimmed = text.trim();
    if (!trimmed || isThinking) return;

    setInput('');
    setError(null);

    // 1. Optimistic UI — show user message immediately
    setMessages(prev => [...prev, { role: 'user', content: trimmed }]);
    setIsThinking(true);

    try {
      // 2. Call LangGraph via the api.js function
      const result = await aiChat(trimmed, threadId);

      // 3. Append AI response with tools metadata
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: result.response || 'Sorry, I could not generate a response.',
        toolsUsed: result.tool_calls_made || [],
      }]);

      // 4. Trigger UI re-fetch if any tools were used, to keep app strictly in sync with AI actions
      if (result.tool_calls_made && result.tool_calls_made.length > 0) {
        window.dispatchEvent(new Event('ai_action_completed'));
      }
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
      // Remove optimistic user message on failure
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsThinking(false);
      inputRef.current?.focus();
    }
  }, [threadId, isThinking]);

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const startNewThread = () => {
    const newId = crypto.randomUUID();
    sessionStorage.setItem(THREAD_KEY, newId);
    setThreadId(newId);
    setMessages([]);
    setError(null);
    setInput('');
    inputRef.current?.focus();
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="agent-chat-page">
      {/* ── Header ── */}
      <div className="agent-chat-header">
        <div>
          <h2 style={{ margin: 0 }}>🤖 AI Agent</h2>
          <p className="muted" style={{ margin: '4px 0 0', fontSize: '0.8rem' }}>
            Thread: <code style={{ fontSize: '0.7rem', opacity: 0.6 }}>{threadId.slice(0, 8)}…</code>
            &nbsp;· Powered by NVIDIA Llama 3.1 + Gemini fallback
          </p>
        </div>
        <button
          className="btn btn-ghost btn-sm"
          onClick={startNewThread}
          title="Clear conversation and start a new thread"
        >
          ✦ New Thread
        </button>
      </div>

      {/* ── Message List ── */}
      <div className="agent-chat-messages">
        {isEmpty && !isThinking && (
          <div className="chat-welcome">
            <div style={{ fontSize: '3rem', marginBottom: 16 }}>🤖</div>
            <h3>Hi! I'm your AI Productivity Agent.</h3>
            <p className="muted" style={{ maxWidth: 480, margin: '0 auto 24px' }}>
              I have live access to your tasks, commitments, and focus sessions.
              I can help you plan, recover from setbacks, and stay on track.
            </p>
            <SuggestedPrompts onSelect={(p) => sendMessage(p)} />
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatMessage key={i} msg={msg} />
        ))}

        {isThinking && <TypingIndicator />}

        {error && (
          <div className="error-banner" style={{ margin: '12px 0' }}>
            ⚠️ {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input Bar ── */}
      <form className="agent-chat-input-bar" onSubmit={handleSubmit}>
        <textarea
          ref={inputRef}
          className="agent-chat-textarea"
          placeholder="Ask me anything about your tasks, commitments, or productivity…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={isThinking}
          id="agent-chat-input"
        />
        <button
          type="submit"
          className="btn btn-primary agent-send-btn"
          disabled={isThinking || !input.trim()}
          id="agent-send-btn"
        >
          {isThinking ? '⏳' : '➤'}
        </button>
      </form>
      <p className="muted" style={{ textAlign: 'center', fontSize: '0.72rem', marginTop: 6 }}>
        Enter to send · Shift+Enter for new line · Responses may take 3-8s while the agent fetches your data
      </p>
    </div>
  );
}
