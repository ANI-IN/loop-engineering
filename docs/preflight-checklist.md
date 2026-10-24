# Preflight checklist for class morning

> **Terms on this page**
>
> - **Live session**: Everything that runs between one `make preflight` and the next.
> - **Planted bug**: A defect switched on by a flag in `.env` so a demo shows its failure every time.
> - **Class-day safeguard**: The version verified in rehearsal, activated with one command if the finale's answer is wrong.

One tick list for the thirty minutes before the four-hour class. Each line is one command or one
look, in order. [The instructor guide](instructor-guide.md) explains each step; this page only
lists them. Run the commands in Ubuntu on WSL2, from the repository root.

## The planted flags

- [ ] `.env` sets every `BUG_` flag and `DEMO_PACING` to 0: the class opens on the fixed system.
      The first planted flag, `BUG_UNBOUNDED_ROWS=1`, is set in Section 1: Agent loop, after the
      confident wrong answer. Set the flags first: the services read `.env` when `make up` starts
      them, so a flag changed after it needs a second restart.

## The services

- [ ] `make up`, then `make ps`: six services up (`postgres`, `api`, `worker`, `scheduler`,
      `hill-climbing-runner`, `console`), `api` and `postgres` healthy; `migrate` has exited.
- [ ] The hill-climbing runner is the Compose service `hill-climbing-runner`. Start no runner of
      your own: `make hill-climbing-runner` refuses while the service serves. To read it:
      `make logs NAME=hill-climbing-runner`.

## The state of each section

- [ ] `make reset NAME=agent-loop`, then `verification-loop`, `event-loop`, and
      `hill-climbing-loop`. Each prints what it cleared; the kill switch is released after each.

## The live session

- [ ] `make preflight PURPOSE=class`: every check passes, the canary lines read `as expected`, and
      the last line starts `Live session started at`.

## The console

- [ ] http://localhost:8501 on the Agent page, in F11 full screen, shared alone.
- [ ] The status line shows the class session's start time, the report-only level, the kill switch
      released, "Business date: 31 January 2026", and "Planted None: the fixed system".

## The class-day safeguard

- [ ] `make safeguard-status` names a version verified in rehearsal. If it says no version is
      verified, the finale runs without the safeguard: read
      [the instructor guide](instructor-guide.md#the-class-day-safeguard-for-the-finale) once.

## LangSmith

- [ ] The newest run of `make live-smoke` the day before found its traces. If it reported a
      missing trace, LangSmith is refusing traces today: in class the live stamp's run id and
      start time are the evidence, and the trace list step is skipped, saying why.
