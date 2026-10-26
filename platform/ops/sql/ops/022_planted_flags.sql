-- Planted flags, recorded where they act (datapilot.planted).
--  * service_planted: each service's own report of the flags its environment switched on when it
--    started (the api, the worker, the scheduler, the hill-climbing runner), rewritten at every
--    start. A live check and the finale refuse while any service reports one. A reset keeps it.
--  * experiments: the flags on for the experiment's runs, as ops.runs records them for a run.

CREATE TABLE ops.service_planted (
    service         text PRIMARY KEY,
    planted_active  text[] NOT NULL DEFAULT '{}',
    started_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE ops.experiments ADD COLUMN planted_active text[] NOT NULL DEFAULT '{}';

GRANT SELECT, INSERT, UPDATE, DELETE ON ops.service_planted TO datapilot_app;
