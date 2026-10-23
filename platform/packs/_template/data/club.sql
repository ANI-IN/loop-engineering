-- The template pack's worked example: Lantern Coffee Club, a coffee subscription business.
-- Load it into both databases of the Compose Postgres as the superuser, one variant each, so the
-- evaluator has two differently seeded copies (use-in-your-repo/README.md, "Try the template"):
--
--   docker compose exec -T postgres psql -U postgres -d datapilot -v variant=1 < platform/packs/_template/data/club.sql
--   docker compose exec -T postgres psql -U postgres -d warehouse_alt -v variant=2 < platform/packs/_template/data/club.sql
--
-- Every row is computed from generate_series, so a load is deterministic. Three business rules
-- hide in the data and are written down only in benchmark/business_rules.md: payment kind 2 is a
-- refund, kind 3 is a test payment, and every day and month is read in Pacific time.

\set ON_ERROR_STOP on

DROP SCHEMA IF EXISTS club CASCADE;
CREATE SCHEMA club AUTHORIZATION datapilot_owner;
SET search_path = club;

CREATE TABLE plans (
    plan_id integer PRIMARY KEY,
    name text NOT NULL,
    monthly_price_cents integer NOT NULL
);

CREATE TABLE members (
    member_id integer PRIMARY KEY,
    email text NOT NULL,
    region text NOT NULL,
    joined_on date NOT NULL,
    marketing_opt_in boolean NOT NULL
);

CREATE TABLE payments (
    payment_id bigint PRIMARY KEY,
    member_id integer NOT NULL REFERENCES members,
    plan_id integer NOT NULL REFERENCES plans,
    paid_ts timestamptz NOT NULL,
    amount_cents integer NOT NULL,
    kind smallint NOT NULL
);

INSERT INTO plans VALUES
    (1, 'Single origin', 1800),
    (2, 'Roaster''s choice', 2400),
    (3, 'Office box', 6500);

-- 240 members in the first database, 300 in the second.
INSERT INTO members
SELECT g,
       'member' || g || '@example.com',
       (ARRAY['north', 'south', 'east', 'west'])[1 + g % 4],
       DATE '2024-01-01' + (g * 3) % 700,
       g % 3 <> 0
FROM generate_series(1, 180 + 60 * :variant) AS g;

-- Monthly charges (kind 1) in 2025. Paid hours are spread over the UTC day, so a payment early in
-- the UTC day belongs to the previous Pacific day, and on the first of a month to the previous
-- Pacific month.
INSERT INTO payments
SELECT m.member_id * 100 + month,
       m.member_id,
       1 + m.member_id % 3,
       TIMESTAMPTZ '2025-01-01 00:00:00+00'
           + make_interval(months => month, days => (m.member_id * 7) % 28,
                           hours => (m.member_id * 5) % 24),
       p.monthly_price_cents,
       1
FROM members m
CROSS JOIN generate_series(0, 11) AS month
JOIN plans p ON p.plan_id = 1 + m.member_id % 3
WHERE (m.member_id + month) % 5 <> 0;

-- Gift boxes (kind 1): one-off charges at the end of each quarter in Pacific time, which is early on
-- the first of the next month in UTC. The amount grows each quarter, so a query that reads the
-- month in UTC moves a different amount in and out of each period.
INSERT INTO payments
SELECT m.member_id * 100 + 90 + quarter,
       m.member_id,
       3,
       TIMESTAMPTZ '2025-04-01 03:00:00+00' + make_interval(months => 3 * quarter),
       2000 + 500 * quarter,
       1
FROM members m
CROSS JOIN generate_series(0, 3) AS quarter
WHERE m.member_id % 6 = 0;

-- Refunds (kind 2): the full charge, three days later, stored as a positive amount.
INSERT INTO payments
SELECT payment_id + 50, member_id, plan_id, paid_ts + interval '3 days', amount_cents, 2
FROM payments
WHERE kind = 1 AND (member_id + (payment_id % 100)) % (7 + 2 * :variant) = 0;

-- Test payments (kind 3): the team's own checks, one per month for the first few members.
INSERT INTO payments
SELECT m.member_id * 100 + month + 70,
       m.member_id,
       1,
       TIMESTAMPTZ '2025-01-15 18:00:00+00' + make_interval(months => month),
       5000,
       3
FROM members m
CROSS JOIN generate_series(0, 11) AS month
WHERE m.member_id <= 2 + :variant;

CREATE VIEW members_marketable AS
SELECT member_id, region, joined_on
FROM members
WHERE marketing_opt_in;

COMMENT ON TABLE payments IS 'One row per payment event.';
COMMENT ON TABLE members IS 'Club members.';
COMMENT ON TABLE plans IS 'Subscription plans.';

-- The agent's read-only role sees the club schema, and nothing in it can change.
GRANT USAGE ON SCHEMA club TO datapilot_agent_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA club TO datapilot_agent_ro;
ANALYZE plans;
ANALYZE members;
ANALYZE payments;
