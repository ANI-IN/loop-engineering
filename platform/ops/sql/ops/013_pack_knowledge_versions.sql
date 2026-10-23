-- Knowledge versions belong to one domain pack (DATAPILOT_PACK), and so do the experiments and gate
-- decisions that name them. Each pack has its own v1, its own candidates, and its own active version,
-- so switching packs never runs one pack's questions under another pack's rules. Rows written before
-- this migration belong to the Harbor & Pine pack, which is also the default for a writer that
-- names no pack.

ALTER TABLE ops.knowledge_versions ADD COLUMN pack text NOT NULL DEFAULT 'datapilot_us';
ALTER TABLE ops.experiments ADD COLUMN pack text NOT NULL DEFAULT 'datapilot_us';
ALTER TABLE ops.promotion_decisions ADD COLUMN pack text NOT NULL DEFAULT 'datapilot_us';

ALTER TABLE ops.experiments DROP CONSTRAINT experiments_knowledge_version_fkey;
ALTER TABLE ops.promotion_decisions DROP CONSTRAINT promotion_decisions_candidate_version_fkey;
ALTER TABLE ops.promotion_decisions DROP CONSTRAINT promotion_decisions_active_version_fkey;

ALTER TABLE ops.knowledge_versions DROP CONSTRAINT knowledge_versions_pkey;
ALTER TABLE ops.knowledge_versions ADD PRIMARY KEY (pack, version);

ALTER TABLE ops.experiments ADD FOREIGN KEY (pack, knowledge_version)
    REFERENCES ops.knowledge_versions (pack, version);
ALTER TABLE ops.promotion_decisions ADD FOREIGN KEY (pack, candidate_version)
    REFERENCES ops.knowledge_versions (pack, version);
ALTER TABLE ops.promotion_decisions ADD FOREIGN KEY (pack, active_version)
    REFERENCES ops.knowledge_versions (pack, version);

-- One active version per pack.
DROP INDEX ops.knowledge_one_active;
CREATE UNIQUE INDEX knowledge_one_active ON ops.knowledge_versions (pack) WHERE status = 'active';

CREATE INDEX experiments_by_pack ON ops.experiments (pack, session_id, started_at);
