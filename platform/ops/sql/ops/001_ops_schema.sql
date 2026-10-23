-- Ops schema: application state for the event loop and the hill-climbing loop.
-- The CHECK lists below are kept equal to datapilot.contracts.lifecycle and autonomy by
-- platform/tests/unit/test_ops_schema_contract.py. ops.run_events is the audit log.

CREATE TABLE ops.events (
    event_id     text PRIMARY KEY,                -- client-supplied; duplicates are absorbed
    source       text NOT NULL,
    type         text NOT NULL CHECK (type IN ('question.asked', 'digest.requested', 'export.requested')),
    payload      jsonb NOT NULL DEFAULT '{}'::jsonb,
    received_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ops.event_duplicates (
    id           bigserial PRIMARY KEY,
    event_id     text NOT NULL REFERENCES ops.events (event_id),
    received_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ops.jobs (
    job_id        bigserial PRIMARY KEY,
    event_id      text NOT NULL UNIQUE REFERENCES ops.events (event_id),
    status        text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'done', 'dead')),
    attempts      integer NOT NULL DEFAULT 0,
    max_attempts  integer NOT NULL DEFAULT 3,
    lease_owner   text,
    lease_until   timestamptz,
    run_after     timestamptz NOT NULL DEFAULT now(),
    last_error    text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX jobs_claimable ON ops.jobs (run_after, job_id) WHERE status = 'queued';
CREATE INDEX jobs_leased ON ops.jobs (lease_until) WHERE status = 'running';

CREATE TABLE ops.runs (
    run_id                  uuid PRIMARY KEY,
    job_id                  bigint REFERENCES ops.jobs (job_id),
    event_id                text REFERENCES ops.events (event_id),
    demo_name               text,
    question                text,
    metric_family           text,
    status                  text NOT NULL CHECK (status IN (
                                'received', 'queued', 'running', 'verifying', 'awaiting_approval',
                                'answered', 'posted', 'rejected', 'failed', 'escalated',
                                'blocked_budget', 'blocked_killswitch')),
    autonomy_level_applied  text CHECK (autonomy_level_applied IN ('report_only', 'assisted', 'unattended')),
    knowledge_version       text,
    model                   text,
    planted_active          text[] NOT NULL DEFAULT '{}',
    tokens_in               integer NOT NULL DEFAULT 0,
    tokens_out              integer NOT NULL DEFAULT 0,
    cost_usd                numeric(12, 6) NOT NULL DEFAULT 0,
    langsmith_url           text,
    answer                  jsonb,
    created_at              timestamptz NOT NULL DEFAULT now(),
    started_at              timestamptz,
    finished_at             timestamptz,
    updated_at              timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX runs_recent ON ops.runs (created_at DESC);

CREATE TABLE ops.run_events (
    id       bigserial PRIMARY KEY,
    run_id   uuid NOT NULL REFERENCES ops.runs (run_id),
    ts       timestamptz NOT NULL DEFAULT now(),
    kind     text NOT NULL CHECK (kind IN (
                 'status_changed', 'tool_call_started', 'tool_call_finished', 'grader_result',
                 'reviewer_verdict', 'approval_requested', 'approval_decided', 'budget_blocked',
                 'killswitch_blocked')),
    payload  jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX run_events_by_run ON ops.run_events (run_id, id);

CREATE TABLE ops.approvals (
    approval_id   bigserial PRIMARY KEY,
    run_id        uuid NOT NULL REFERENCES ops.runs (run_id),
    requested_at  timestamptz NOT NULL DEFAULT now(),
    action        text NOT NULL,                  -- what will run, exactly as shown to the approver
    sql           text,
    row_estimate  bigint,
    reason        text NOT NULL,
    decision      text CHECK (decision IN ('approve', 'reject')),
    decided_by    text,
    decided_at    timestamptz,
    comment       text
);
CREATE UNIQUE INDEX approvals_one_open_per_run ON ops.approvals (run_id) WHERE decision IS NULL;

CREATE TABLE ops.posts (
    post_id     bigserial PRIMARY KEY,
    channel     text NOT NULL,
    run_id      uuid REFERENCES ops.runs (run_id),
    event_id    text REFERENCES ops.events (event_id),
    label       text NOT NULL,                    -- such as "unverified" at the report-only level
    body        jsonb NOT NULL,
    posted_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX posts_recent ON ops.posts (channel, posted_at DESC);

CREATE TABLE ops.control (
    id              smallint PRIMARY KEY CHECK (id = 1),
    kill_switch     text NOT NULL DEFAULT 'released' CHECK (kill_switch IN ('released', 'armed', 'engaged')),
    autonomy_level  text NOT NULL DEFAULT 'report_only' CHECK (autonomy_level IN ('report_only', 'assisted', 'unattended')),
    changed_at      timestamptz NOT NULL DEFAULT now(),
    changed_by      text NOT NULL DEFAULT 'system',
    reason          text
);
INSERT INTO ops.control (id) VALUES (1);

CREATE TABLE ops.budgets (
    day          date PRIMARY KEY,                -- the Eastern time calendar day
    token_limit  bigint NOT NULL,
    tokens_used  bigint NOT NULL DEFAULT 0
);

CREATE TABLE ops.autonomy_policy (
    metric_family   text PRIMARY KEY,
    level           text NOT NULL DEFAULT 'report_only' CHECK (level IN ('report_only', 'assisted', 'unattended')),
    eligible_since  timestamptz,
    demoted_at      timestamptz,
    reason          text
);

CREATE TABLE ops.knowledge_versions (
    version         text PRIMARY KEY,
    yaml            text NOT NULL,
    status          text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'active', 'retired')),
    created_by      text NOT NULL,
    approved_by     text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    approved_at     timestamptz,
    activated_at    timestamptz,
    experiment_ids  uuid[] NOT NULL DEFAULT '{}'
);
CREATE UNIQUE INDEX knowledge_one_active ON ops.knowledge_versions ((status)) WHERE status = 'active';

CREATE TABLE ops.experiments (
    experiment_id      uuid PRIMARY KEY,
    knowledge_version  text NOT NULL REFERENCES ops.knowledge_versions (version),
    split              text NOT NULL CHECK (split IN ('dev', 'holdout', 'all')),
    holdout_repeats    integer NOT NULL DEFAULT 3,
    concurrency        integer NOT NULL DEFAULT 8,
    pass_count         integer,
    total              integer,
    per_example        jsonb NOT NULL DEFAULT '[]'::jsonb,
    langsmith_url      text,
    tokens             bigint NOT NULL DEFAULT 0,
    cost_usd           numeric(12, 6) NOT NULL DEFAULT 0,
    started_at         timestamptz NOT NULL DEFAULT now(),
    finished_at        timestamptz,
    wall_seconds       numeric(10, 2)
);

CREATE TABLE ops.promotion_decisions (
    decision_id        bigserial PRIMARY KEY,
    candidate_version  text NOT NULL REFERENCES ops.knowledge_versions (version),
    active_version     text NOT NULL REFERENCES ops.knowledge_versions (version),
    verdict            text NOT NULL CHECK (verdict IN ('promoted', 'blocked')),
    reasons            jsonb NOT NULL,
    sentence           text NOT NULL,             -- the plain-sentence verdict the console shows
    approved_by        text,
    decided_at         timestamptz NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ops TO datapilot_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ops TO datapilot_app;
