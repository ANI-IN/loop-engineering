-- The agent role: read-only, warehouse schema only. Applied by `make seed` as the superuser on
-- both databases (datapilot and warehouse_alt), after the warehouse tables exist. The values in
-- braces come from limits in pack.yaml. The bootstrap script already revoked TEMP on the database
-- and CREATE on schema public from PUBLIC; nothing here grants anything on ops or lg.

REVOKE ALL ON ALL TABLES IN SCHEMA warehouse FROM datapilot_agent_ro;
GRANT USAGE ON SCHEMA warehouse TO datapilot_agent_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA warehouse TO datapilot_agent_ro;

-- Session defaults at login. default_transaction_read_only is a seatbelt that a session can turn
-- off; the SELECT-only grants above are the real boundary.
ALTER ROLE datapilot_agent_ro SET default_transaction_read_only = on;
ALTER ROLE datapilot_agent_ro SET statement_timeout = {statement_timeout};
ALTER ROLE datapilot_agent_ro SET idle_in_transaction_session_timeout = {idle_timeout};
ALTER ROLE datapilot_agent_ro SET temp_file_limit = {temp_file_limit};
ALTER ROLE datapilot_agent_ro SET search_path = warehouse;
