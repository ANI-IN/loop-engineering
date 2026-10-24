-- When LangSmith refused the upload of a run's trace for its free plan's monthly trace limit, as the
-- worker that uploaded it saw it (loop3_events.trace_refusals). NULL: no refusal was seen, which is
-- not proof the trace arrived. The live smoke check reads it through the api's run record, since
-- only the worker's own process sees the refusal of the traces it uploads.

ALTER TABLE ops.runs ADD COLUMN trace_refused_at timestamptz;
