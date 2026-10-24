-- ops.experiments had tokens and cost_usd columns that nothing ever wrote: every experiment read
-- 0 tokens and 0 dollars, whatever it spent. An experiment's spend is in the spend ledger (make
-- spend, by activity) and in each run's trace; the columns are dropped so no reader can take the
-- zeros for a measurement. Numbered 019 so another track's migration of the same review can take
-- 018. Archived experiment rows (ops.reset_archive_rows) keep the two fields as they were.

ALTER TABLE ops.experiments DROP COLUMN tokens, DROP COLUMN cost_usd;
