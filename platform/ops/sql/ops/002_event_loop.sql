-- Event loop state beyond the foundation schema (the loops track).
--  * jobs: a queue name from the router, and 'parked' for a job whose run waits for human approval
--    (the approval puts the same job back in the queue, so one event keeps one job).
--  * approvals: what kind of approval it is (a tool call paused before it ran, or a held answer).
--  * control: a restart request the worker obeys (demo control, guarded by an environment switch).
--  * autonomy_policy: the knowledge version under which a family became eligible.
--  * improvement_requests: experiment and analyzer requests for the hill-climbing loop's runner.

ALTER TABLE ops.jobs DROP CONSTRAINT jobs_status_check;
ALTER TABLE ops.jobs ADD CONSTRAINT jobs_status_check
    CHECK (status IN ('queued', 'running', 'parked', 'done', 'dead'));
ALTER TABLE ops.jobs ADD COLUMN queue text NOT NULL DEFAULT 'default';
DROP INDEX ops.jobs_claimable;
CREATE INDEX jobs_claimable ON ops.jobs (queue, run_after, job_id) WHERE status = 'queued';

ALTER TABLE ops.approvals ADD COLUMN kind text NOT NULL DEFAULT 'tool_call'
    CHECK (kind IN ('tool_call', 'held_answer'));

ALTER TABLE ops.control ADD COLUMN worker_restart_requested_at timestamptz;

ALTER TABLE ops.autonomy_policy ADD COLUMN knowledge_version text;

CREATE TABLE ops.improvement_requests (
    request_id         uuid PRIMARY KEY,
    kind               text NOT NULL CHECK (kind IN ('experiment', 'analyzer')),
    params             jsonb NOT NULL DEFAULT '{}'::jsonb,
    status             text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'done', 'failed')),
    session_id         uuid,             -- ops.live_sessions (migration 010 comes later, so no FK)
    requested_by       text NOT NULL,
    requested_at       timestamptz NOT NULL DEFAULT now(),
    started_at         timestamptz,
    finished_at        timestamptz,
    result             jsonb
);
CREATE INDEX improvement_requests_queued ON ops.improvement_requests (requested_at) WHERE status = 'queued';

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ops TO datapilot_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ops TO datapilot_app;
