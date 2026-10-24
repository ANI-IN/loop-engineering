-- The experiment of the active version that a candidate's gate compared it with. The background
-- promotion decides an approved version against this one, never against the active version's
-- newest experiment: a run of the active version after the gate made the gate read as unfinished,
-- so the approved version was never decided and held the finale's controls (review round 3).
-- No foreign key: the hill-climbing reset deletes experiments, and a candidate whose recorded
-- baseline is gone waits, with a hold message that names the way out.

ALTER TABLE ops.experiments ADD COLUMN gate_baseline_id uuid;
