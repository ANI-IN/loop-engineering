-- Only the owner role records migrations. Migration 001 granted the app role writes on every ops
-- table that existed then, and ops.schema_migrations already did (db.migrate creates it first), so
-- the role the api and the worker run as could mark a migration applied or not applied.

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ops.schema_migrations FROM datapilot_app;
