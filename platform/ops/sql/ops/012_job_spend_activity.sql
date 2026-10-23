-- The spend-ledger activity travels with the work. POST /events records the activity its caller
-- names (the DataPilot-Spend-Activity header) on the event's job, and the worker records every
-- model call of that job under it. NULL: the worker's own DATAPILOT_SPEND_ACTIVITY applies.

ALTER TABLE ops.jobs ADD COLUMN spend_activity text
    CHECK (spend_activity IS NULL OR length(spend_activity) BETWEEN 1 AND 100);
