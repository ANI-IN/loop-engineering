-- Live sessions: every demo result belongs to the class session it was run in.
-- `make preflight` starts a session once its checks pass; the console shows only runs and experiments
-- of the current session, so an older result can never stand in for a live one.
-- Numbered 010 so track migrations 002 to 009 keep their order.

CREATE TABLE ops.live_sessions (
    session_id   uuid PRIMARY KEY,
    started_at   timestamptz NOT NULL DEFAULT now(),
    started_by   text NOT NULL,
    timezone     text NOT NULL,                   -- the instructor's local time zone, for the live stamp
    ended_at     timestamptz
);
CREATE UNIQUE INDEX live_sessions_one_open ON ops.live_sessions ((ended_at IS NULL)) WHERE ended_at IS NULL;

ALTER TABLE ops.runs ADD COLUMN session_id uuid REFERENCES ops.live_sessions (session_id);
ALTER TABLE ops.experiments ADD COLUMN session_id uuid REFERENCES ops.live_sessions (session_id);
CREATE INDEX runs_by_session ON ops.runs (session_id, created_at DESC);
CREATE INDEX experiments_by_session ON ops.experiments (session_id, started_at DESC);

GRANT SELECT, INSERT, UPDATE ON ops.live_sessions TO datapilot_app;
