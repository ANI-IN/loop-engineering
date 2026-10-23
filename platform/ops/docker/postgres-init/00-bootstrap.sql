-- Runs once, as the superuser, when the Compose Postgres volume is created.
-- Roles, databases, and schemas only. Warehouse tables and the agent role's grants and settings are
-- applied by `make seed` (platform/ops/sql/roles.sql); ops tables by `make migrate`.
-- Passwords are for the local Compose database only and match .env.example.

CREATE ROLE datapilot_owner LOGIN PASSWORD 'datapilot_owner';
CREATE ROLE datapilot_app LOGIN PASSWORD 'datapilot_app';
CREATE ROLE datapilot_agent_ro LOGIN PASSWORD 'datapilot_agent_ro';

CREATE DATABASE datapilot OWNER datapilot_owner;
CREATE DATABASE warehouse_alt OWNER datapilot_owner;

\connect datapilot
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE TEMP ON DATABASE datapilot FROM PUBLIC;
GRANT TEMP ON DATABASE datapilot TO datapilot_owner, datapilot_app;
CREATE SCHEMA warehouse AUTHORIZATION datapilot_owner;
CREATE SCHEMA ops AUTHORIZATION datapilot_owner;
-- The LangGraph checkpointer creates its own tables in schema lg (no schema option exists, so the
-- app connects to it with search_path=lg).
CREATE SCHEMA lg AUTHORIZATION datapilot_app;
GRANT USAGE ON SCHEMA ops TO datapilot_app;

\connect warehouse_alt
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE TEMP ON DATABASE warehouse_alt FROM PUBLIC;
CREATE SCHEMA warehouse AUTHORIZATION datapilot_owner;
