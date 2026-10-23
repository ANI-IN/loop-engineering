-- The candidates of each analyzer request. The analyzer team writes analyzer.candidates rule sets
-- (pack.yaml) from the same failed dev items; each runs on the dev split only, and the hill-climbing
-- runner keeps one, by fewer dev regressions, then more dev passes, then fewer rules. Every
-- candidate is one row here, the kept one marked chosen, so the Improve page and the reports can
-- show the choice. The naive analyzer writes one row with no dev measurement. A candidate's own
-- rules are saved in ops.knowledge_versions under candidate_version, retired at once, so it is never
-- offered for approval; the kept one is saved again as the draft named saved_as.
-- A database migrated while this file was named 015_analyzer_candidates.sql already has the table:
-- it is created only when missing, and that older record is replaced by this one, so the count of
-- applied migrations still matches the files.

DELETE FROM ops.schema_migrations WHERE name = '015_analyzer_candidates.sql';

CREATE TABLE IF NOT EXISTS ops.analyzer_candidates (
    candidate_id       bigserial PRIMARY KEY,
    pack               text NOT NULL,
    session_id         uuid REFERENCES ops.live_sessions (session_id),
    request_id         uuid,             -- ops.improvement_requests; empty for a call outside one
    from_version       text NOT NULL,    -- the active version the failed dev items came from
    saved_as           text NOT NULL,    -- the draft offered for approval
    label              text NOT NULL CHECK (label ~ '^[A-Z]$'),
    candidate_version  text NOT NULL,
    chosen             boolean NOT NULL,
    naive              boolean NOT NULL DEFAULT false,
    dev_passes         integer,          -- empty when the candidate had no dev measurement
    dev_total          integer,
    dev_regressions    text[] NOT NULL DEFAULT '{}',
    rules              integer NOT NULL,  -- rules the candidate adds to from_version
    guard_flags        integer NOT NULL DEFAULT 0,  -- rules the overfit guard flags
    sentence           text NOT NULL,    -- the request's whole choice, as the console shows it
    created_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS analyzer_candidates_by_session ON ops.analyzer_candidates (session_id, created_at);

GRANT SELECT, INSERT ON ops.analyzer_candidates TO datapilot_app;
GRANT USAGE, SELECT ON SEQUENCE ops.analyzer_candidates_candidate_id_seq TO datapilot_app;
