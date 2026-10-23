-- The hill-climbing reset archives, then deletes, the open session's analyzer candidates
-- (ops.analyzer_candidates, migration 016), as it does the session's experiments.

GRANT DELETE ON ops.analyzer_candidates TO datapilot_app;
