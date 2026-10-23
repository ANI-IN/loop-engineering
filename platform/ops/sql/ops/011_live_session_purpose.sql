-- Each live session records why it was started: the class, a rehearsal, the Thursday review, or
-- development. `make preflight PURPOSE=<purpose>` starts it once every check passes and ends the
-- previous one (datapilot.contracts.live).

ALTER TABLE ops.live_sessions
    ADD COLUMN purpose text NOT NULL DEFAULT 'development'
        CHECK (purpose IN ('class', 'rehearsal', 'thursday-review', 'development'));
