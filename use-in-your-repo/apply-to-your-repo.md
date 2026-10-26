# Apply the loops to your own data

> **Terms on this page**
>
> - **Domain pack**: The folder that holds one warehouse's settings, rules, benchmark, and knowledge.
> - **Trap**: A business rule the schema does not reveal, so a plausible query gets it wrong.
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
> - **Live session**: Everything that runs between one `make preflight` and the next.

Three parts, in order. Part 1 runs the template pack, Lantern Coffee Club, on the Compose Postgres,
so you see every file of a pack work before you write your own. Part 2 builds your own pack. Part 3
points DataPilot at your own Postgres. Every Structured Query Language (SQL) file and command below
exists in this repository; the template's files are in `platform/packs/_template/`.

Finish the [setup](../setup/README.md) first: `make up`, `make seed`, and `make preflight
PURPOSE=development` must work with the Harbor & Pine pack.

## One setting selects the pack

`DATAPILOT_PACK` in `.env` names the folder under `platform/packs/` that every process reads: the
analyst, the graders, the evaluator, the console, the knowledge versions, and the preflight checks.
It is `datapilot_us`, the Harbor & Pine pack, when it is not set. Three places stay with Harbor &
Pine, so nothing surprises you later:

| Place | What it does | What you do |
|---|---|---|
| `make seed`, `make check-data` | Load and check the Harbor & Pine warehouses | Load your own data yourself, as in part 1, step 1 |
| `platform/demos/registry.yaml` | The class demos, with Harbor & Pine questions | Ask your own questions on the console; run your benchmark |
| The assignments | Their checks run on the Harbor & Pine pack | Set `DATAPILOT_PACK` back before you run one |

## Part 1: run the template pack

### Step 1: Load the example data

**Why.** The template's gold queries need the tables they read. `data/club.sql` creates schema
`club` with three tables and a view, fills them from `generate_series` so every load is the same,
and grants the agent's read-only role `SELECT` on it. Loading it with variant 1 and variant 2 gives
two differently seeded databases, as the evaluator needs.

**Do this.** From the repository root, with the services up:

```bash
docker compose exec -T postgres psql -U postgres -d datapilot -v variant=1 < platform/packs/_template/data/club.sql
docker compose exec -T postgres psql -U postgres -d warehouse_alt -v variant=2 < platform/packs/_template/data/club.sql
```

The Compose superuser is local to your machine (`compose.yaml`); never use a superuser for the
agent.

**Check it worked.** Each command ends with `ANALYZE` and no `ERROR` line.

### Step 2: Check the pack

**Why.** `check_pack.py` reads the pack through the platform's own loaders: `pack.yaml` against
every setting the platform reads, the benchmark against the `BenchmarkItem` contract, the starting
knowledge, the preflight checks, and the business rules file. With the database, it runs every
gold query on both databases through the read-only executor, proves each naive query gives a
different answer, and runs the preflight data check as the agent's role. It makes no model call.

**Do this.**

```bash
make check-pack PACK=_template
```

`make check-pack` runs `uv run python use-in-your-repo/check_pack.py _template --database`. Without
`--database`, the same script checks only the files, with no database.

**You should see.** One `ok` line per check, then the summary. The last lines on the course
machine:

> Your output will differ: run times, ids, and the agent's wording change on every run.

```text
ok net-revenue-south-2025: the gold query runs on both databases
ok net-revenue-south-2025: the naive query differs from gold
ok preflight data check: 2,785 payments in club.payments
check_pack: _template: 0 problems
```

**If it fails.** Each `x` line names the setting, the item, or the query. A naive query that gives
the same answer as gold means the data cannot catch that trap: add rows that make them differ.

### Step 3: Point DataPilot at the template

**Why.** Every process reads the pack named by `DATAPILOT_PACK`. The services read `.env` when
they start, so they see the change after `make up`.

**Do this.** In `.env`, set one line:

```ini
DATAPILOT_PACK=_template
```

Then restart the services and start a session with the template's own checks:

```bash
make up
make preflight PURPOSE=development
```

Preflight reads its checks from `preflight` in the template's `pack.yaml`: the data check counts
`club.payments` as the agent's role, and the canary asks the five questions named in
`preflight.canary`. The canary's model calls use your key.

**Check it worked.** Preflight prints `ok pack: _template` and `ok data: 2,785 payments in
club.payments`, and its last line starts `Live session started at`. On the console's
Agent page, ask "What was our net revenue in March 2025, in dollars?". Under the starting knowledge
the answer is wrong: the analyst does not know refunds or test payments.

### Step 4: Run the template's benchmark

**Why.** This is the hill-climbing loop on a new domain: a baseline experiment, the analyzer team on
the failed dev items, and the gate on the holdout split.

**Do this.** On the Improve page, Run experiment on the active version, or:

```bash
make demo NAME=improve-baseline-experiment
```

Then Run analyzer, read the knowledge diff, and run the experiment on the candidate, as in
[Section 4: Hill-climbing loop](../section-4-hill-climbing-loop/README.md). The
`hill-climbing-runner` service that `make up` starts serves the Improve page; `make ps` shows it.
After a change to `DATAPILOT_PACK` in `.env`, run `make up` so it reads the new pack.

**Check it worked.** The holdout ledger shows the template's four holdout items.

### Step 5: Switch back

Set `DATAPILOT_PACK=datapilot_us` again, or delete the line, then `make up` and `make preflight
PURPOSE=development`. Each pack keeps its own knowledge versions in the ops tables: its own `v1`,
its own candidates, and its own active version. The switch never runs one pack's questions under
the other pack's rules, and `make reset NAME=hill-climbing-loop` clears only the selected pack's
candidates.

## Part 2: build your own domain pack

### Step 1: Copy the template

```bash
cp -r platform/packs/_template platform/packs/my_pack
```

Use a readable folder name, and set `name:` in the copy's `pack.yaml` to the same name.

### Step 2: Write the business rules first

Write `benchmark/business_rules.md` before any query. For every number your team reports, write
each rule a new analyst could not read from the schema: a fiscal calendar, a status code, an
excluded group, a time zone. Mark at least three as traps, each with a short id such as `refunds`.
A trap is a rule where the plausible query gives a different answer.

### Step 3: Write the benchmark

Write `benchmark/dev.yaml` and `benchmark/holdout.yaml`, one `BenchmarkItem` per question
(`platform/src/datapilot/contracts/evaluation.py`):

- `gold_sql` for every question, written by hand and following every rule;
- `naive_sql` and `traps` for every trap question: the query a model without the rules writes;
- `metric_family` for every question, from `autonomy.metric_families` in `pack.yaml`;
- holdout questions worded away from the dev questions, so the analyzer team cannot learn them.

The gate decides on the holdout split, and each holdout item runs 3 times per version
(`evaluation.holdout_repeats`), so a small holdout costs little and a large one is more evidence.

### Step 4: Keep the starting knowledge near-empty

Keep `knowledge/v1.yaml` as the template ships it: the money rule only. Every other rule is for
the hill-climbing loop to learn and the gate to prove. Your pack's versions are its own in the ops
tables, so its `v1` never mixes with the Harbor & Pine pack's.

### Step 5: Set the pack's safety settings

In `pack.yaml`, change only the lines marked `YOURS`:

- `databases.allowed_schema`: the one schema the agent may read;
- `personal_data.columns`: every column with personal data, as `schema.table.column`; a query that
  reads one waits for human approval;
- `personal_data.marketing_view`: a view in the same schema that holds none of those columns;
- `autonomy.metric_families`: the families your benchmark uses;
- `preflight.data_check`: a table in your schema that must hold rows, and what one row is;
- `preflight.canary`: three easy items without traps, and two trap items.

### Step 6: Check it

```bash
make check-pack PACK=my_pack
```

Fix every `x` line, then follow part 1, steps 3 and 4, with `DATAPILOT_PACK=my_pack`.

## Part 3: point DataPilot at your own Postgres

### Step 1: Create a read-only role

**Why.** The database role is the boundary, not the parser. The agent role may read one schema and
nothing else, and every transaction is read-only. `platform/ops/sql/roles.sql` is the Harbor &
Pine version.

**Do this.** As an administrator of your database, replace `club` with your schema and choose a
password:

```sql
CREATE ROLE datapilot_agent_ro LOGIN PASSWORD 'choose-a-password';
REVOKE ALL ON ALL TABLES IN SCHEMA club FROM datapilot_agent_ro;
GRANT USAGE ON SCHEMA club TO datapilot_agent_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA club TO datapilot_agent_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA club GRANT SELECT ON TABLES TO datapilot_agent_ro;
ALTER ROLE datapilot_agent_ro SET default_transaction_read_only = on;
ALTER ROLE datapilot_agent_ro SET statement_timeout = '5000ms';
ALTER ROLE datapilot_agent_ro SET idle_in_transaction_session_timeout = '10000ms';
ALTER ROLE datapilot_agent_ro SET temp_file_limit = '102400kB';
ALTER ROLE datapilot_agent_ro SET search_path = club;
```

The values are `limits.statement_timeout_ms`, `limits.idle_in_transaction_timeout_ms`, and
`limits.temp_file_limit_kb` in `pack.yaml`. The revoke comes first, so the role starts from
nothing even if it existed. The default privileges cover tables created later, but only those
created by the role that runs the line: run it as the role that creates your tables. Setting
`temp_file_limit` needs a superuser; without one, leave that line out, and nothing caps the
temporary files one query writes. `search_path` makes an unqualified table name resolve in your schema only.

**Check it worked.** As that role, a write fails with `permission denied` or `cannot execute ...
in a read-only transaction`. If a write succeeds, stop: revoke every privilege except `SELECT`.

### Step 2: Give the evaluator a second database

The evaluator compares results on two databases, so a wrong query cannot pass by coincidence. Use
a second copy of your schema with different rows: a staging copy, or a copy with a sample of the
rows. Give the same read-only role access to it.

### Step 3: Point the agent at your databases

In `.env`, set the two agent addresses to your databases, twice: once as the commands on your
machine reach them, and once as the services in Docker reach them:

```ini
DATABASE_URL_AGENT=postgresql://datapilot_agent_ro:choose-a-password@your-host:5432/your_database
DATABASE_URL_AGENT_ALT=postgresql://datapilot_agent_ro:choose-a-password@your-host:5432/your_second_database
SERVICES_DATABASE_URL_AGENT=postgresql://datapilot_agent_ro:choose-a-password@your-host:5432/your_database
SERVICES_DATABASE_URL_AGENT_ALT=postgresql://datapilot_agent_ro:choose-a-password@your-host:5432/your_second_database
```

Inside a container, `localhost` is the container itself, so the `SERVICES_` lines need an address
the containers can reach. Without the `SERVICES_` lines, the services use the Compose Postgres.
Keep `DATABASE_URL_OWNER` and `DATABASE_URL_APP` on the Compose Postgres: the ops tables, the
queue, and the approvals stay there. For a database on another machine, `compose.yaml` needs no
change.

**A Postgres on this same machine.** In the `SERVICES_` lines, use `host.docker.internal` as
`your-host`. Docker Desktop on Windows and macOS provides that name. Docker Engine on Linux, the
course machine's setup, provides it only when a service asks for it. Add a file
`compose.override.yaml` next to `compose.yaml`; `docker compose`, and so `make up`, reads it on its
own:

```yaml
services:
  api: {extra_hosts: ["host.docker.internal:host-gateway"]}
  worker: {extra_hosts: ["host.docker.internal:host-gateway"]}
  scheduler: {extra_hosts: ["host.docker.internal:host-gateway"]}
  hill-climbing-runner: {extra_hosts: ["host.docker.internal:host-gateway"]}
  console: {extra_hosts: ["host.docker.internal:host-gateway"]}
```

Your Postgres must also accept connections from the Docker network: `listen_addresses` in
`postgresql.conf` and a `pg_hba.conf` line for that network.

### Step 4: Run it

```bash
make check-pack PACK=my_pack
make up
make preflight PURPOSE=development
```

Then ask a question on the console's Agent page, and run your benchmark from the Improve page.

## If it fails

| You see | Cause | Fix |
|---|---|---|
| `x pack.yaml has every setting the platform reads: ...` | A key is missing from your copy | Copy it back from the template |
| `x ...: the naive query differs from gold` | The data gives the naive query the right answer | Add rows that expose the trap |
| `x ...: the gold query runs on both databases` | The gold SQL fails, or the two databases disagree | Run the gold query by hand as the agent role |
| The agent sees no tables | The role has no `USAGE` or `SELECT`, or `allowed_schema` is wrong | Step 1 of part 3, and `databases.allowed_schema` |
| `no pack '...': ... does not exist (check DATAPILOT_PACK)` | `DATAPILOT_PACK` names no folder under `platform/packs/` | Set it to your pack's folder name |
| `x data: ... is not readable as the agent's role` | The pack's data is not loaded, or the agent role cannot read it | Part 1, step 1, or part 3, step 1 |
| `x data: 0 ... in ...` | The data check's table is empty | Load your data, or name a table with rows in `preflight.data_check` |
