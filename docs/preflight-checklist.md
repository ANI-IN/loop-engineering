# Preflight checklist for class morning

> **Terms on this page**
>
> - **Live session**: Everything that runs between one `make preflight` and the next.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
> - **Class-day safeguard**: The version verified in rehearsal, activated with one command if the finale's answer is wrong.

One tick list for the thirty minutes before the four-hour class. Each line is one command or one
look, in order. [The instructor guide](instructor-guide.md) explains each step; this page only
lists them. Run the commands in Ubuntu on WSL2, from the repository root.

## The planted flags

- [ ] `.env` sets every `BUG_` flag and `DEMO_PACING` to 0, and keeps them there all day: each
      planted half is `make demo NAME=<demo> PLANTED=1`, its flags on for its own runs only. The
      finale and every live check refuse to start while a flag is on.

## The rehearsal's images

- [ ] At the end of the rehearsal, the day before: `make check-images ARGS=--rehearsal` passed. It
      fails on any image the rehearsal still owes a retake
      ([the instructor guide](instructor-guide.md#the-day-before), step 10).

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

- [ ] The rehearsal ran on an earlier Eastern time day than the class: preflight for the class
      refuses while fewer tokens than one class run-through needs, about 520,000, are left of the
      day's token budget, and the count starts again only at midnight Eastern time.
- [ ] `make preflight PURPOSE=class`: every check passes, including `token budget`, the canary
      lines read `as expected`, and the last line starts `Live session started at`.
- [ ] Only if it refuses with "Less than one class pass is left of this Eastern time day's token
      budget": no class session started, and the session open before it, often the rehearsal
      one, stays open, so teach nothing in it. Tell the course owner. Then run the command at the
      end of the message, `make preflight PURPOSE=class ACCEPT_TOKENS_LEFT=<count>`, with the
      digits of the printed command, without commas: the class session starts, knowingly. With 0
      tokens left the message offers no command, and no class session starts that day.
      Plan the cuts with
      [the instructor guide's steps](instructor-guide.md#if-something-breaks) ("The token budget
      refusal"): the planted half of the unbounded rows demo goes first.

## The console

- [ ] http://localhost:8501 on the Agent page, in F11 full screen, shared alone.
- [ ] The status line shows the class session's start time, the report-only level, the kill switch
      released, "Business date: 31 January 2026", and "Planted None: the fixed system".

## The class-day safeguard

- [ ] `make safeguard-status` names a version verified in rehearsal and prints the line
      `ok make safeguard-activate takes it`. If it prints `x  make safeguard-activate refuses it`,
      the version is older than 7 days or not from a rehearsal session of this stack: treat it as
      no version. If it says no version is verified, the finale runs without the safeguard: read
      [the instructor guide](instructor-guide.md#the-class-day-safeguard-for-the-last-run) once.

## LangSmith

- [ ] The newest run of `make live-smoke` the day before found its traces. If it reported a
      missing trace, LangSmith is refusing traces today: in class the live stamp's run id and
      start time are the evidence, and the trace list step is skipped, saying why.
