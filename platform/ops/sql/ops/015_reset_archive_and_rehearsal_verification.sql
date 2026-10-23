-- Two records the hill-climbing loop keeps (decisions 9 and 2 on session report 2). Numbered 015 so
-- another track's migration of the same session can take 014.
--
-- 1. The reset archive. Before `make reset` deletes or retires a row, it copies the row here,
--    whole, as JSON, under one archive entry per reset stamped with the reset time and the live
--    session open at the time. Experiments keep their per-item results and confirmations (they are
--    columns of the experiment row). The app role may add and read, never change or delete.
-- 2. Rehearsal verification, for the class-day safeguard. A knowledge version is marked "verified
--    in rehearsal" with who, when, and the run id of its correct finale (the run's gold check
--    passed), with the metric families it had cleared under its own clearance record then. If the
--    version promoted live in class gives a wrong finale answer, one command activates the
--    verified version and records it in ops.promotion_decisions as a safeguard activation.

CREATE TABLE ops.reset_archives (
    reset_id            uuid PRIMARY KEY,
    section             text NOT NULL,
    pack                text NOT NULL,
    discarded_baseline  boolean NOT NULL DEFAULT false,
    session_id          uuid,             -- the live session open at the reset; no foreign key, so
                                          -- the archive outlives any cleanup of ops.live_sessions
    reset_at            timestamptz NOT NULL DEFAULT now(),
    reset_by            text NOT NULL
);
CREATE INDEX reset_archives_recent ON ops.reset_archives (reset_at DESC);

CREATE TABLE ops.reset_archive_rows (
    archive_row_id  bigserial PRIMARY KEY,
    reset_id        uuid NOT NULL REFERENCES ops.reset_archives (reset_id),
    source_table    text NOT NULL,                -- ops.experiments, ops.promotion_decisions, ...
    row_key         text NOT NULL,                -- the row's primary key, as text
    action          text NOT NULL CHECK (action IN ('deleted', 'retired')),
    row             jsonb NOT NULL                -- the whole row as it was before the reset
);
CREATE INDEX reset_archive_rows_by_key ON ops.reset_archive_rows (source_table, row_key);
CREATE INDEX reset_archive_rows_by_reset ON ops.reset_archive_rows (reset_id);

CREATE TABLE ops.rehearsal_verifications (
    verification_id   bigserial PRIMARY KEY,
    pack              text NOT NULL,
    version           text NOT NULL,
    verified_by       text NOT NULL,
    verified_at       timestamptz NOT NULL DEFAULT now(),
    session_id        uuid NOT NULL,              -- the rehearsal session of the finale run
    finale_run_id     uuid NOT NULL,              -- a run that may later be reset: its facts are here
    finale_question   text NOT NULL,
    finale_level      text NOT NULL CHECK (finale_level IN ('report_only', 'assisted', 'unattended')),
    agent_value       text,
    gold_value        text,
    langsmith_url     text,
    cleared_families  text[] NOT NULL DEFAULT '{}', -- cleared under this version's own record then
    FOREIGN KEY (pack, version) REFERENCES ops.knowledge_versions (pack, version)
);
CREATE INDEX rehearsal_verifications_by_version ON ops.rehearsal_verifications (pack, version);

-- A gate decision, or the class-day safeguard's activation of a version verified in rehearsal.
ALTER TABLE ops.promotion_decisions ADD COLUMN kind text NOT NULL DEFAULT 'gate'
    CHECK (kind IN ('gate', 'safeguard'));

GRANT SELECT, INSERT ON ops.reset_archives, ops.reset_archive_rows, ops.rehearsal_verifications
    TO datapilot_app;
GRANT USAGE, SELECT ON ops.reset_archive_rows_archive_row_id_seq,
    ops.rehearsal_verifications_verification_id_seq TO datapilot_app;
