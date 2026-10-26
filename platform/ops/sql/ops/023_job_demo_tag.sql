-- The tag of a demo's run whose demo restarted the worker with a flag read at its start
-- (datapilot.planted.TAG_HEADER). A worker restarted with a tag claims only the jobs that carry
-- it, so the flag never reaches another run; a worker without a tag claims every job.

ALTER TABLE ops.jobs ADD COLUMN demo_tag text;
