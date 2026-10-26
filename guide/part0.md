# Part 0: Before you start

Part 0 gets the class machine ready: the services up, the warehouse checked, every section reset,
a class session started with its drift canary, and the console on screen. Run it thirty minutes
before class, in order. The first time on a machine, finish the [setup pages](../setup/README.md)
first; they include the install and the first live demo.

## What you need

- A set-up copy of the repository, with your two keys in `.env`: the OpenAI key from the operations
  team and your own LangSmith key. Never paste a key into a terminal, a document, or a chat.
- The display the class sees. Present the console in full screen (F11): the run board is laid out
  for a page of 1280 by 720 pixels (`platform/console/DESIGN.md`).
- Two terminals in the repository folder: the stack terminal, for the services, and the demo
  terminal, for every `make demo` and `make reset`. The chapters name them.

> Your output will differ: run times, ids, and the agent's wording change on every run.

### Step 1: Start the services

**Where:** The stack terminal, in the repository folder.

**Type:**

```bash
make up
make ps
```

**You should see:** the image build, then the containers starting. `make ps` on the course machine
on 25 October 2026:

![The terminal output of make ps: six services, api, console, hill-climbing-runner, postgres, scheduler, and worker, each with status Up, api and postgres marked healthy, and the ports of api, console, and postgres bound to 127.0.0.1 only](../docs/images/part0-make-ps-terminal.png)

*Six services up, the hill-climbing runner among them; `api` and `postgres` are healthy, and every port is bound to `127.0.0.1`, this machine only.*

**Look at:** the STATUS column.

**What it means:** every service is up, and `api` and `postgres` passed their health checks.

> [!CHECKPOINT]
> Every service shows `Up`, and `api` and `postgres` show `(healthy)`.

> [!IFDIFFERENT]
> `Cannot connect to the Docker daemon` → start Docker (`sudo systemctl start docker` in Ubuntu), then `make up`.
> A service keeps restarting → `make logs NAME=<service>` shows why.

> [!INSTRUCTOR]
> Do this before learners join. If a service is down later in class, `make up` again: the queue and
> pending approvals survive in Postgres.

### Step 2: Check the warehouse

**Where:** The stack terminal.

**Type:**

```bash
make check-data
```

**You should see:** one line per warehouse with its row counts and content hash. The last line on
the course machine:

```text
check-data: both warehouses match expected.yaml
```

**Look at:** that last line.

**What it means:** both warehouses hold exactly the seeded data the benchmark's gold queries expect.

> [!CHECKPOINT]
> The last line matches, with no `x` line before it.

> [!IFDIFFERENT]
> An `x` line names a table → run `make seed`, then `make check-data` again.

> [!INSTRUCTOR]
> No model call yet: nothing so far costs anything.

### Step 3: Reset every section

**Where:** The demo terminal.

**Type:**

```bash
make reset NAME=agent-loop
make reset NAME=verification-loop
make reset NAME=event-loop
make reset NAME=hill-climbing-loop
```

**You should see:** one confirmation per section. The hill-climbing reset says what it kept.

![The terminal output of the four resets: each section's reset lists the tables it cleared; the hill-climbing reset also names the baseline experiment it kept, the candidate version it removed, the retired versions it kept, the active knowledge version v1, and the reset archive of the rows it changed](../docs/images/part0-four-resets-terminal.png)

*Each reset says what it cleared; the hill-climbing reset keeps the session's baseline, leaves version 1 of the knowledge (the starting version) active, and archives every row it changed.*

**Look at:** the last line of each reset.

**What it means:** each section's live run state is cleared and the kill switch is released.
The reset does not change the planted flags: they stay at `0` in `.env` all day, and each planted
half sets its own with `make demo NAME=<demo> PLANTED=1`.

> [!CHECKPOINT]
> Every reset ends without an error line.

> [!IFDIFFERENT]
> A reset cannot reach the database → Step 1 again.

> [!INSTRUCTOR]
> The hill-climbing reset keeps a session's baseline experiment. Never use
> `make reset-discarding-baseline` to recover in class.

### Step 4: Start the class session

**Where:** The demo terminal.

**Type:**

```bash
make preflight PURPOSE=class
```

The class session is the instructor's. On your own copy after class, type
`make preflight PURPOSE=development` instead.

**You should see:** one line per check starting with `ok`, one `canary` line per question ending in
`as expected` with its trace link, and a last line that starts with `Live session started at`.

![The terminal output of make preflight: seven ok lines for the pack, postgres, the data, the api, the console, the OpenAI key with gpt-6-luna, and the knowledge, then five canary lines, three easy questions passed and two trap questions failed, each as expected with its trace link, and the line Live session started at 12:42:50 with model id gpt-6-luna](../docs/images/part0-preflight-terminal.png)

*PURPOSE=rehearsal shown; class prints the same lines with purpose class. Each canary line ends "as expected"; 12 warning lines and a trace-limit notice are left out.*

**Look at:** the last line: the session's start time and the model id, `gpt-6-luna`.

**What it means:** the services, the warehouse, your key, and the model all work, and the drift
canary still behaves as calibration measured: three easy questions pass and two trap questions
still fail. Everything from now until the next preflight belongs to this class session.

> [!CHECKPOINT]
> The last line starts with `Live session started at` and names `gpt-6-luna`.

> [!IFDIFFERENT]
> `Your OpenAI key was not accepted. Check it with the operations team.` → the key in `.env` is missing or rejected; ask the operations team.
> `The drift canary failed: ...` → the model changed; do not teach the measured results as they are, and re-run calibration.
> `Less than one class pass is left of this Eastern time day's token budget ...` (only with `PURPOSE=class`) → no class session started, and the session open before it, often the rehearsal one, stays open: teach nothing in it. Less than about 520,000 tokens is left of the stack's daily token budget. Tell the course owner, then run the command at the end of the message, `make preflight PURPOSE=class ACCEPT_TOKENS_LEFT=<count>`, with the digits of the printed command, without commas: the class session starts knowingly, and the worker blocks every run once the cap is reached. Cut the planted half of the unbounded rows demo first, as [the instructor guide](../docs/instructor-guide.md#if-something-breaks) says under "The token budget refusal".

> [!INSTRUCTOR]
> Run preflight once. Never run it again during class: a new session orphans the class baseline.
> Rehearse on an earlier Eastern time day than the class: the `token budget` line shows the day's
> count, which starts again only at midnight Eastern time.
> The canary asks five questions, each one agent run: about 40 model calls, under a cent.

### Step 5: Put the console on screen

**Where:** The browser, at http://localhost:8501.

**Type:** open the Events page, then press F11 for full screen.

**You should see:** the status line above the run board.

![The status line and run board as they look in class: the report-only level, no family cleared, the session start, the business date 31 January 2026, tokens today against the daily cap, Planted None: the fixed system, and the five lanes](../section-3-event-loop/demo/expected/events-webhook-question-board.png)

*The status line in class: report-only level, business date 31 January 2026, and no planted bug; this capture, of 24 October 2026, already holds one posted run, run ce15ac5d.*

**Look at:** "Planted None: the fixed system" and "Business date: 31 January 2026".

**What it means:** every demo starts from the fixed system, at the report-only level, on the
course's business date. Times on the console are in your local time.

> [!CHECKPOINT]
> The status line, all five lanes, and the off-the-board row fit on the screen without scrolling.

> [!IFDIFFERENT]
> The console is blank → `make ps`; if the console service is up, try http://127.0.0.1:8501.
> "No live session." → Step 4.

> [!INSTRUCTOR]
> Keep the terminals and the editor in separate windows, and share only the console window.
