-- =====================================================
-- AI Productivity Assistant — Supabase Schema
-- Run in: Supabase Dashboard > SQL Editor
-- =====================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    google_id VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(200),
    avatar_url VARCHAR(500),
    preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);

CREATE TABLE IF NOT EXISTS commitments (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (type IN ('bill','interview','assignment','event','other')),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    due_date DATE NOT NULL,
    amount NUMERIC,
    source VARCHAR(50) DEFAULT 'manual',
    priority_score FLOAT DEFAULT 0.0,
    risk_score FLOAT DEFAULT 0.0,
    root_cause VARCHAR(100),
    root_cause_score FLOAT,
    is_done BOOLEAN DEFAULT FALSE,
    is_missed BOOLEAN DEFAULT FALSE,
    metadata_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_commitments_user ON commitments(user_id);
CREATE INDEX IF NOT EXISTS idx_commitments_due_date ON commitments(due_date);

CREATE TABLE IF NOT EXISTS tasks (
    id BIGSERIAL PRIMARY KEY,
    commitment_id BIGINT NOT NULL REFERENCES commitments(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    due_date DATE,
    order_index INTEGER DEFAULT 0,
    is_done BOOLEAN DEFAULT FALSE,
    estimated_minutes INTEGER DEFAULT 25,
    actual_minutes INTEGER DEFAULT 0,
    pomodoros_estimated INTEGER DEFAULT 1,
    pomodoros_completed INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tasks_commitment ON tasks(commitment_id);

CREATE TABLE IF NOT EXISTS focus_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id BIGINT REFERENCES tasks(id) ON DELETE SET NULL,
    mode VARCHAR(20) NOT NULL CHECK (mode IN ('pomodoro','flowtime','deepwork','break')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','running','completed','cancelled','interrupted')),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    planned_duration_minutes INTEGER DEFAULT 25,
    actual_duration_minutes INTEGER DEFAULT 0,
    pomodoro_number INTEGER DEFAULT 1,
    is_break BOOLEAN DEFAULT FALSE,
    flow_rating FLOAT CHECK (flow_rating BETWEEN 1 AND 5),
    contributed_to_streak BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_focus_user ON focus_sessions(user_id, started_at DESC);

CREATE TABLE IF NOT EXISTS reminders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    commitment_id BIGINT NOT NULL REFERENCES commitments(id) ON DELETE CASCADE,
    style VARCHAR(50) NOT NULL CHECK (style IN ('deadline','achievement','consequence','streak')),
    message TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    user_action VARCHAR(50),
    action_time TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id, sent_at DESC);

CREATE TABLE IF NOT EXISTS feedback (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    commitment_id BIGINT NOT NULL REFERENCES commitments(id) ON DELETE CASCADE,
    reason VARCHAR(100) NOT NULL,
    detail TEXT,
    feedback_time TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$ language 'plpgsql';

CREATE TRIGGER update_commitments_updated_at BEFORE UPDATE ON commitments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS (backend uses service_role key — bypasses RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE commitments ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE focus_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE reminders ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
