-- ============================================================================
-- supabase_schema.sql
-- AI Productivity Assistant — Full Database Schema
--
-- INSTRUCTIONS:
-- 1. Open your Supabase Dashboard
-- 2. Go to SQL Editor (left sidebar)
-- 3. Paste this entire file and click "Run"
-- 4. All tables, indexes, RLS policies, and Realtime will be configured
--
-- Auth Strategy: Backend uses SERVICE_ROLE key (bypasses RLS).
-- Frontend Realtime uses ANON key (enforced by RLS).
-- ============================================================================

-- ============================================================================
-- SECTION 1: EXTENSIONS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- For future text search


-- ============================================================================
-- SECTION 2: TABLES
-- ============================================================================

-- ── users ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                  BIGSERIAL PRIMARY KEY,
    google_id           TEXT UNIQUE,                              -- Google OAuth sub (nullable — Supabase auth users won't have this)
    supabase_uid        UUID UNIQUE,                              -- Supabase Auth user UUID
    email               TEXT UNIQUE NOT NULL,
    name                TEXT,
    avatar_url          TEXT,
    google_access_token TEXT,
    google_refresh_token TEXT,
    google_token_expiry TIMESTAMPTZ,
    preferences         JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT users_email_not_empty CHECK (email != '')
);

COMMENT ON TABLE users IS 'Application users. Supports both Google OAuth and Supabase Auth.';
COMMENT ON COLUMN users.google_id IS 'Set when user signs in via Google OAuth custom flow.';
COMMENT ON COLUMN users.supabase_uid IS 'Set when user signs in via Supabase Auth. Links to auth.users.id.';


-- ── channels ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS channels (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    color       TEXT NOT NULL DEFAULT '#10B981',
    order_index INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE channels IS 'User-defined tags/categories for tasks (e.g., Work, Personal, Health).';


-- ── commitments ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS commitments (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type             TEXT NOT NULL,                               -- project, habit, deadline, goal, financial
    title            TEXT NOT NULL,
    description      TEXT,
    due_date         DATE NOT NULL,
    amount           NUMERIC,                                     -- For financial commitments
    source           TEXT NOT NULL DEFAULT 'manual',             -- manual, ai, import, google_calendar
    priority_score   FLOAT NOT NULL DEFAULT 0.0,                 -- 0-100, computed by PriorityEngine
    risk_score       FLOAT NOT NULL DEFAULT 0.0,                 -- 0.0-1.0, computed by RiskEngine
    root_cause       TEXT,                                        -- AI-predicted procrastination root cause
    root_cause_score FLOAT,
    is_done          BOOLEAN NOT NULL DEFAULT FALSE,
    is_missed        BOOLEAN NOT NULL DEFAULT FALSE,
    metadata_json    JSONB NOT NULL DEFAULT '{}',                 -- AI reasoning, raw_text, confidence, external IDs
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE commitments IS 'High-level goals/projects. Parent of tasks. Scored by AI engines.';


-- ── weekly_plans ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS weekly_plans (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    week_start_date     DATE NOT NULL,                            -- Always Monday
    week_end_date       DATE NOT NULL,                            -- Always Sunday
    title               TEXT NOT NULL,
    description         TEXT,
    channel_id          BIGINT REFERENCES channels(id) ON DELETE SET NULL,
    commitment_id       BIGINT REFERENCES commitments(id) ON DELETE SET NULL,
    target_focus_hours  FLOAT NOT NULL DEFAULT 0.0,              -- Planned hours for this week
    actual_focus_hours  FLOAT NOT NULL DEFAULT 0.0,              -- Tracked hours (updated by focus sessions)
    status              TEXT NOT NULL DEFAULT 'planned',          -- planned, in_progress, done, missed
    ai_generated        BOOLEAN NOT NULL DEFAULT FALSE,           -- Was this AI-suggested?
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT weekly_plans_status_check CHECK (status IN ('planned', 'in_progress', 'done', 'missed'))
);

COMMENT ON TABLE weekly_plans IS 'Weekly intention blocks. Hierarchy: Commitment → WeeklyPlan → DailyPlan → Task.';


-- ── daily_plans ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_plans (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_date           DATE NOT NULL,
    weekly_plan_id      BIGINT REFERENCES weekly_plans(id) ON DELETE SET NULL,
    morning_intention   TEXT,                                     -- User's written startup ritual
    shutdown_time       TIME,                                     -- Planned end-of-work time
    energy_level        SMALLINT,                                 -- 1-5 scale (set at start of day)
    mood                TEXT,                                     -- focused, tired, motivated, anxious, neutral
    notes               TEXT,                                     -- End-of-day freeform reflection
    is_complete         BOOLEAN NOT NULL DEFAULT FALSE,           -- Shutdown ritual completed?
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT daily_plans_unique_date UNIQUE (user_id, plan_date),
    CONSTRAINT daily_plans_energy_range CHECK (energy_level IS NULL OR (energy_level >= 1 AND energy_level <= 5))
);

COMMENT ON TABLE daily_plans IS 'Day-level structured planning. One per user per day. Auto-created by GET /api/daily-plans/today.';


-- ── tasks ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    commitment_id       BIGINT REFERENCES commitments(id) ON DELETE CASCADE,
    weekly_plan_id      BIGINT REFERENCES weekly_plans(id) ON DELETE SET NULL,
    daily_plan_id       BIGINT REFERENCES daily_plans(id) ON DELETE SET NULL,
    channel_id          BIGINT REFERENCES channels(id) ON DELETE SET NULL,
    title               TEXT NOT NULL,
    description         TEXT,
    priority            TEXT NOT NULL DEFAULT 'none',             -- none, low, medium, high, urgent
    order_index         INT NOT NULL DEFAULT 0,
    is_done             BOOLEAN NOT NULL DEFAULT FALSE,
    due_date            DATE,
    planned_date        DATE,                                     -- Date this task is scheduled for (Today view)
    start_time          TIME,
    end_time            TIME,
    estimated_minutes   INT NOT NULL DEFAULT 25,
    actual_minutes      INT NOT NULL DEFAULT 0,
    pomodoros_estimated INT NOT NULL DEFAULT 1,
    pomodoros_completed INT NOT NULL DEFAULT 0,
    google_event_id     TEXT,                                     -- Google Calendar event ID
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT tasks_priority_check CHECK (priority IN ('none', 'low', 'medium', 'high', 'urgent'))
);

COMMENT ON TABLE tasks IS 'Atomic work units. Can be standalone, commitment subtasks, or weekly/daily plan tasks.';


-- ── daily_highlights ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_highlights (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    daily_plan_id   BIGINT REFERENCES daily_plans(id) ON DELETE SET NULL,
    date            DATE NOT NULL,
    highlight_type  TEXT NOT NULL DEFAULT 'shutdown',             -- startup, shutdown, milestone, gratitude
    content         TEXT NOT NULL,                                -- Main AI/manual highlight text
    ai_summary      TEXT,                                         -- Short AI-generated summary
    tasks_completed INT NOT NULL DEFAULT 0,                       -- Snapshot at shutdown time
    focus_minutes   INT NOT NULL DEFAULT 0,                       -- Total focus minutes that day
    mood_end        TEXT,                                         -- End-of-day mood
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT daily_highlights_type_check CHECK (highlight_type IN ('startup', 'shutdown', 'milestone', 'gratitude'))
);

COMMENT ON TABLE daily_highlights IS 'AI-generated and manual journal highlights. Generated by shutdown ritual.';


-- ── focus_sessions ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS focus_sessions (
    id                       BIGSERIAL PRIMARY KEY,
    user_id                  BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id                  BIGINT REFERENCES tasks(id) ON DELETE SET NULL,
    daily_plan_id            BIGINT REFERENCES daily_plans(id) ON DELETE SET NULL,
    mode                     TEXT NOT NULL,                       -- pomodoro, deepwork, flowtime, break
    status                   TEXT NOT NULL DEFAULT 'pending',     -- pending, running, completed, cancelled, interrupted
    started_at               TIMESTAMPTZ,
    ended_at                 TIMESTAMPTZ,
    planned_duration_minutes INT NOT NULL DEFAULT 25,
    actual_duration_minutes  INT NOT NULL DEFAULT 0,
    pomodoro_number          INT NOT NULL DEFAULT 1,
    is_break                 BOOLEAN NOT NULL DEFAULT FALSE,
    flow_rating              FLOAT,                               -- 1.0-5.0 user self-rating
    contributed_to_streak    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT focus_sessions_mode_check CHECK (mode IN ('pomodoro', 'deepwork', 'flowtime', 'break')),
    CONSTRAINT focus_sessions_status_check CHECK (status IN ('pending', 'running', 'completed', 'cancelled', 'interrupted'))
);

COMMENT ON TABLE focus_sessions IS 'Pomodoro/deep work session tracking. is_break sessions excluded from analytics.';


-- ── reminders ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reminders (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    commitment_id BIGINT NOT NULL REFERENCES commitments(id) ON DELETE CASCADE,
    style         TEXT NOT NULL,                                  -- deadline, achievement, consequence, streak
    message       TEXT NOT NULL,
    sent_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_action   TEXT,                                           -- dismissed, postponed, done
    action_time   TIMESTAMPTZ
);

COMMENT ON TABLE reminders IS 'AI-generated nudge notifications linked to commitments.';


-- ── feedback ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feedback (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    commitment_id BIGINT NOT NULL REFERENCES commitments(id) ON DELETE CASCADE,
    reason        TEXT NOT NULL,                                  -- procrastination, blocked, changed_priority, etc.
    detail        TEXT,
    feedback_time TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE feedback IS 'User postponement reasons. Feeds Root Cause and Personalization AI engines.';


-- ============================================================================
-- SECTION 3: INDEXES (Performance)
-- ============================================================================

-- Users
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_supabase_uid ON users(supabase_uid) WHERE supabase_uid IS NOT NULL;

-- Commitments
CREATE INDEX IF NOT EXISTS idx_commitments_user_id ON commitments(user_id);
CREATE INDEX IF NOT EXISTS idx_commitments_due_date ON commitments(due_date);
CREATE INDEX IF NOT EXISTS idx_commitments_priority ON commitments(user_id, priority_score DESC) WHERE is_done = FALSE;

-- Weekly Plans
CREATE INDEX IF NOT EXISTS idx_weekly_plans_user_id ON weekly_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_weekly_plans_week_start ON weekly_plans(user_id, week_start_date);

-- Daily Plans
CREATE INDEX IF NOT EXISTS idx_daily_plans_user_date ON daily_plans(user_id, plan_date);

-- Tasks (most queried table)
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_planned_date ON tasks(user_id, planned_date) WHERE planned_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_daily_plan ON tasks(daily_plan_id) WHERE daily_plan_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_weekly_plan ON tasks(weekly_plan_id) WHERE weekly_plan_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_commitment ON tasks(commitment_id) WHERE commitment_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_incomplete ON tasks(user_id, is_done) WHERE is_done = FALSE;

-- Daily Highlights
CREATE INDEX IF NOT EXISTS idx_highlights_user_date ON daily_highlights(user_id, date DESC);

-- Focus Sessions
CREATE INDEX IF NOT EXISTS idx_focus_user_status ON focus_sessions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_focus_started_at ON focus_sessions(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_focus_daily_plan ON focus_sessions(daily_plan_id) WHERE daily_plan_id IS NOT NULL;


-- ============================================================================
-- SECTION 4: AUTO-UPDATE updated_at TRIGGER
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'users', 'channels', 'commitments', 'weekly_plans',
        'daily_plans', 'tasks', 'daily_highlights'
    ]
    LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS set_updated_at ON %I; 
             CREATE TRIGGER set_updated_at
             BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();',
            tbl, tbl
        );
    END LOOP;
END $$;


-- ============================================================================
-- SECTION 5: ROW LEVEL SECURITY (RLS)
-- ============================================================================
-- Backend uses service role key → bypasses RLS (no policy needed for backend)
-- Frontend Realtime uses anon key → enforced by these policies

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE commitments ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_highlights ENABLE ROW LEVEL SECURITY;
ALTER TABLE focus_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE reminders ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

-- ── Helper function: get app user id from Supabase JWT ───────────────────────
-- Maps supabase auth.uid() → our users.id
-- Used by RLS policies for frontend realtime connections
CREATE OR REPLACE FUNCTION get_app_user_id()
RETURNS BIGINT AS $$
    SELECT id FROM users WHERE supabase_uid = auth.uid()
$$ LANGUAGE SQL SECURITY DEFINER STABLE;


-- ── RLS Policies ─────────────────────────────────────────────────────────────

-- users: users can only see their own row
CREATE POLICY "users_own_row" ON users
    FOR ALL USING (supabase_uid = auth.uid() OR id = get_app_user_id());

-- channels
CREATE POLICY "channels_own_data" ON channels
    FOR ALL USING (user_id = get_app_user_id());

-- commitments
CREATE POLICY "commitments_own_data" ON commitments
    FOR ALL USING (user_id = get_app_user_id());

-- weekly_plans
CREATE POLICY "weekly_plans_own_data" ON weekly_plans
    FOR ALL USING (user_id = get_app_user_id());

-- daily_plans
CREATE POLICY "daily_plans_own_data" ON daily_plans
    FOR ALL USING (user_id = get_app_user_id());

-- tasks
CREATE POLICY "tasks_own_data" ON tasks
    FOR ALL USING (user_id = get_app_user_id());

-- daily_highlights
CREATE POLICY "highlights_own_data" ON daily_highlights
    FOR ALL USING (user_id = get_app_user_id());

-- focus_sessions
CREATE POLICY "focus_sessions_own_data" ON focus_sessions
    FOR ALL USING (user_id = get_app_user_id());

-- reminders
CREATE POLICY "reminders_own_data" ON reminders
    FOR ALL USING (user_id = get_app_user_id());

-- feedback
CREATE POLICY "feedback_own_data" ON feedback
    FOR ALL USING (user_id = get_app_user_id());


-- ============================================================================
-- SECTION 6: REALTIME (Enable publication for all tables)
-- ============================================================================
-- This allows frontend to subscribe to INSERT/UPDATE/DELETE events

-- Add all tables to the realtime publication
ALTER PUBLICATION supabase_realtime ADD TABLE tasks;
ALTER PUBLICATION supabase_realtime ADD TABLE daily_plans;
ALTER PUBLICATION supabase_realtime ADD TABLE weekly_plans;
ALTER PUBLICATION supabase_realtime ADD TABLE commitments;
ALTER PUBLICATION supabase_realtime ADD TABLE channels;
ALTER PUBLICATION supabase_realtime ADD TABLE daily_highlights;
ALTER PUBLICATION supabase_realtime ADD TABLE focus_sessions;
ALTER PUBLICATION supabase_realtime ADD TABLE reminders;

-- ============================================================================
-- DONE!
-- After running this script:
-- 1. Update your backend/.env with the 4 Supabase credentials
-- 2. Restart the FastAPI backend — it will auto-create any missing SQLAlchemy tables
-- 3. Test via GET /health — should show "database: connected"
-- ============================================================================
