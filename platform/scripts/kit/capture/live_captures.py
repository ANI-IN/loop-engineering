"""Live console captures of one section, from live runs on the class stack, for the lead to run.

    uv run python platform/scripts/kit/capture/live_captures.py <section> [--only NAME]...
        [--half fixed|planted] [--paced] [--chain-step STEP] [--attempts N] [--dry-run]

Every image is a live run: this runner makes model calls through the class stack (the spend goes to
the ledger under DATAPILOT_SPEND_ACTIVITY), so only the lead runs it, with the stack up. It never
starts the stack, never changes .env, and never sets a planted flag in the stack: the planted half
(`--half planted`) and demo pacing (`--paced`) are switched on for the demo's own runs alone, as
`make demo NAME=<demo> PLANTED=1` does (commands.demo_running: the flags in the header of the
demo's own events, and a flag read as a service starts on a worker restarted for the demo's runs
alone).

For Sections 1 to 3, for each image of the section in live_manifest.py whose half is the one asked
for, it:

1. reads the stack's planted flags: it sends the zero-token malicious SQL check and, once the run
   has finished, reads its planted_active (the api's flags and the worker's, which it adds as it
   takes the run), and refuses every image when any flag is on, for either half;
2. resets the section as the class does (`make reset NAME=<section>`: commands.reset);
3. opens the console page in Chromium (1280 by 720, device scale factor 2, Coordinated Universal
   Time, no browser chrome, the pointer parked; the Agent page, the default, at the console's
   root, and a "Page not found" dialog stops the capture) and triggers the registry demo with
   datapilot.loop3_events.commands.demo, the function `make demo NAME=` calls;
4. waits for each moment's state in the run's own record through the api (GET /runs/{id}), does a
   person's step the way the console does (Restart worker is pressed on the page, as the
   restart's outcome line belongs to the page that pressed it; approval is POST /approvals/{id},
   the dialog's call, after Review has opened the dialog in a page of its own for its image; the
   kill switch is armed and engaged by the demo, as the status line does),
   then frames the element the manifest names (capture kit framing.py: the whole viewport, no edge
   across text) and writes the PNG to its repository path and every copy;
5. checks each written image with platform/scripts/check_images.py, and logs every run id, request
   id, fact for the captions, and problem in a JSON log (.runs/live-captures/ by default).

A state that never comes (the run answered without a number, a layer other than the expected one)
writes no image: the section is reset and the demo triggered again, up to `--attempts` times.

Section 4's images come from the hill-climbing chain, which the lead drives in the instructor
guide's order. With `--chain-step STEP` the runner triggers nothing and resets nothing: it waits
until the chain is in that step's state (GET /improvement/requests and the page), then captures
the step's images.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / "pyproject.toml").is_file())
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "platform" / "scripts"))

import framing  # noqa: E402
import live_manifest as manifest  # noqa: E402
from live_manifest import Record, Shot  # noqa: E402

LOG_FOLDER = REPO / ".runs" / "live-captures"
RUN_TIMEOUT = 400.0  # seconds; the slowest Section 1 to 3 demo measured about 60
CHAIN_TIMEOUT = 2400.0
PAGE_SETTLE = 3.0  # seconds after the state is in the record: three fragment ticks of the page
RETRY_TIMEOUT = 900.0  # the missing retry cap runs until the cap per run; measured up to minutes
NOT_FOUND = "Page not found"  # Streamlit's dialog for a path the console does not serve


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Api:
    """The api over HTTP, retrying a dropped connection (WSL port forwarding drops some), with the
    spend activity header so the worker records each run under this process's activity."""

    def __init__(self, url: str) -> None:
        import httpx

        from datapilot.observability import spend

        self.httpx = httpx
        self.client = httpx.Client(base_url=url, timeout=60, headers=spend.activity_headers())

    def post(self, path: str, **kwargs: Any) -> Any:
        return self._retry("POST", path, **kwargs)

    def get(self, path: str, **kwargs: Any) -> Any:
        return self._retry("GET", path, **kwargs)

    def _retry(self, method: str, path: str, **kwargs: Any) -> Any:
        for attempt in range(3):
            try:
                return self.client.request(method, path, **kwargs)
            except (self.httpx.RemoteProtocolError, self.httpx.ConnectError, self.httpx.ReadError):
                if attempt == 2:
                    raise
                time.sleep(3)
        raise AssertionError("unreachable")

    def json(self, path: str, **kwargs: Any) -> Any:
        response = self.get(path, **kwargs)
        response.raise_for_status()
        return response.json()

    def run(self, run_id: str) -> dict[str, Any]:
        return dict(self.json(f"/runs/{run_id}"))

    def wait(
        self,
        run_id: str,
        check: Callable[[dict[str, Any]], list[str]],
        timeout: float = RUN_TIMEOUT,
    ) -> tuple[dict[str, Any], list[str]]:
        """Poll the run until `check` finds no problem or the run has finished otherwise."""
        deadline = time.monotonic() + timeout
        while True:
            found = self.run(run_id)
            problems = check(found)
            if not problems:
                return found, []
            settled = found["status"] in manifest.FINISHED - {"awaiting_approval"}
            if settled or time.monotonic() > deadline:
                return found, problems
            time.sleep(2)


class Capture:
    """One browser page on the console, and the images written from it."""

    def __init__(self, browser: Any, console: str, page: str) -> None:
        self.context = framing.new_context(browser)
        self.page = self.context.new_page()
        self.page.goto(f"{console}/{manifest.page_path(page)}")
        self.page.locator(manifest.STATUS_LINE).first.wait_for(timeout=60_000)
        time.sleep(PAGE_SETTLE)
        if self.page.get_by_text(NOT_FOUND).count():  # the dialog would cover every image
            self.close()
            raise LookupError(f"the console has no page at /{manifest.page_path(page)}")

    def close(self) -> None:
        self.context.close()

    def shoot(self, shot: Shot, record: Record, run_id: str | None = None) -> None:
        """Frame the shot and write it to its paths only when the frame holds its moment: no
        dialog or error in view, no edge across text, every must_see element wholly in the
        frame, and nothing the image check reports. A refused frame is kept for review under
        .runs/live-captures/refused/, never at the image's path."""
        import check_images

        seen = shot.seen(run_id)
        # A strip deep in a lane: its list is scrolled to it before every screenshot tried.
        data, edges = framing.framed_screenshot(
            self.page, top=shot.top, bottom=shot.bottom, lanes=seen
        )
        record.edges = edge_record(edges)
        trial = LOG_FOLDER / "refused" / f"{shot.name}.png"
        trial.parent.mkdir(parents=True, exist_ok=True)
        trial.write_bytes(data)
        record.image_check = [
            f"{p.kind}: {p.detail}" for p in check_images.check_image(trial, shot.path)
        ]
        places = framing.where(self.page, seen)
        refusals = manifest.frame_problems(
            blockers=framing.blockers(self.page, allow_dialog=shot.dialog),
            edges_clean=edges.clean,
            edges=record.edges,
            missing=[s for s, place in places.items() if place in framing.NOT_IN_FRAME],
            image_check=record.image_check,
            hidden=[s for s, place in places.items() if place == framing.HIDDEN],
        )
        if refusals:
            record.problems = [*record.problems, *refusals]
            print(f"x {shot.path}: not written ({'; '.join(refusals)}); the frame is in {trial}")
            return
        trial.unlink()
        for relative in shot.paths:
            target = REPO / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        record.written = True
        record.captured_at = now()
        copies = " (and its copies)" if shot.copies else ""
        print(f"+ {shot.path}{copies}: edges {record.edges}")

    def unmarked_notes(self) -> list[str]:
        """Trap notes of the annotated query with no numbered mark on a fragment of it."""
        notes = self.page.locator(f"{manifest.SQL} .notes li .n").all_inner_texts()
        tags = set(self.page.locator(f"{manifest.SQL} sup.tag").all_inner_texts())
        return [n for n in notes if n not in tags]

    def wait_text(self, text: str, timeout: float = 60.0) -> bool:
        try:
            self.page.get_by_text(text).first.wait_for(timeout=timeout * 1000)
        except Exception:
            return False
        return True

    def wait_selector(self, selector: str, timeout: float = 60.0) -> bool:
        try:
            self.page.locator(selector).first.wait_for(timeout=timeout * 1000)
        except Exception:
            return False
        return True


def edge_record(edges: framing.Edges) -> dict[str, int]:
    """What the log keeps of a frame's edges: the colour changes and the strokes among them."""
    return {
        "top": edges.top,
        "bottom": edges.bottom,
        "header": edges.header,
        "top_strokes": edges.top_strokes,
        "bottom_strokes": edges.bottom_strokes,
    }


def finished(run: dict[str, Any]) -> list[str]:
    return [] if run["status"] in manifest.FINISHED else [f"the run is {run['status']}"]


def strip_in(lane: str, run_id: str) -> str:
    return f'.list[data-lane="{lane}"] article.strip[data-run="{run_id}"]'


# --- Sections 1 to 3: one scenario per registry demo -----------------------------------------
class Section:
    def __init__(self, args: argparse.Namespace, api: Api, browser: Any) -> None:
        self.args = args
        self.api = api
        self.browser = browser
        self.console = args.console.rstrip("/")
        self.flags: list[str] = []  # on for the scenario's demo's own runs, never in the stack
        self.demos = contextlib.ExitStack()  # the demo triggered in this attempt, until it ends

    def trigger(self, demo: str) -> Any:
        """The demo, as make demo NAME=<demo> [PLANTED=1] sends it: its flags in the header of its
        own events (a service-start flag on a worker restarted for its runs alone), held until
        the attempt ends."""
        from datapilot.loop3_events import commands

        running = commands.demo_running(demo, self.flags, client=self.api)
        return self.demos.enter_context(running)

    def reset(self) -> None:
        from datapilot.loop3_events import commands

        for line in commands.reset(self.args.section).lines():
            print(f"  {line}")

    def run_scenario(self, scenario: str, shots: list[Shot]) -> list[Record]:
        records = {s.name: Record(s.name, list(s.paths), s.scenario, s.moment) for s in shots}
        for attempt in range(1, self.args.attempts + 1):
            for record in records.values():
                record.attempt, record.problems, record.written = attempt, [], False
            print(f"- {scenario}, attempt {attempt}")
            self.reset()
            self.flags = sorted(expected_for(shots))
            capture = Capture(self.browser, self.console, shots[0].page)
            try:
                SCENARIOS[scenario](self, capture, shots, records)
            except Exception as error:  # the log says what failed; the next attempt starts clean
                for record in records.values():
                    if not record.written:
                        record.problems.append(f"{type(error).__name__}: {error}")
            finally:
                try:
                    capture.close()
                finally:  # the demo's flags end with the attempt; a restarted service goes back
                    self.demos.close()
            if all(r.written for r in records.values()):
                break
        return list(records.values())


def _take(
    capture: Capture,
    shots: list[Shot],
    records: dict[str, Record],
    moment: str,
    run: dict[str, Any],
    problems: list[str],
) -> None:
    """Every shot of `moment`: written when the state check found no problem."""
    for shot in shots:
        if shot.moment != moment:
            continue
        record = records[shot.name]
        record.run_ids = sorted({*record.run_ids, str(run["run_id"])})
        record.facts = manifest.facts(run)
        if problems:
            record.problems = list(problems)
            continue
        capture.shoot(shot, record, str(run["run_id"]))


def agent_simple_question(section: Section, capture: Capture, shots, records) -> None:
    run_id = section.trigger("agent-simple-question").run_ids[0]
    run, problems = section.api.wait(run_id, manifest.simple_question)
    if not problems:
        capture.wait_text("No trap found in this query")
    time.sleep(PAGE_SETTLE)
    _take(capture, shots, records, "answered", run, problems)


def agent_unbounded_rows(section: Section, capture: Capture, shots, records) -> None:
    half = shots[0].half
    run_id = section.trigger("agent-unbounded-rows").run_ids[0]
    run, problems = section.api.wait(run_id, lambda r: manifest.unbounded_rows(r, half))
    if not problems:  # the tokens line at the page's end, as the run record has it
        capture.wait_text(f"{manifest.tokens(run):,} tokens")
    time.sleep(PAGE_SETTLE)
    _take(capture, shots, records, "finished", run, problems)


def _trap_notes(section: Section, capture: Capture, check: Callable, demo: str, shots, records):
    run_id = section.trigger(demo).run_ids[0]
    run, problems = section.api.wait(run_id, check)
    if not problems:  # the gold check is written by the worker after the run finishes
        deadline = time.monotonic() + 180
        while manifest.gold(run) is None and time.monotonic() < deadline:
            time.sleep(3)
            run = section.api.run(run_id)
        problems = check(run)
    if not problems:
        capture.wait_selector(f"{manifest.SQL} .notes li")
        time.sleep(PAGE_SETTLE)
        unmarked = capture.unmarked_notes()
        if unmarked:  # the owner's rule: every trap note has its mark in the query
            problems = [f"trap notes {unmarked} have no mark in the query"]
    _take(capture, shots, records, "answered", run, problems)


def agent_confident_wrong_answer(section, capture, shots, records) -> None:
    _trap_notes(
        section,
        capture,
        manifest.confident_wrong_answer,
        "agent-confident-wrong-answer",
        shots,
        records,
    )


def verify_graders_pass_still_wrong(section, capture, shots, records) -> None:
    _trap_notes(
        section,
        capture,
        manifest.graders_pass_still_wrong,
        "verify-graders-pass-still-wrong",
        shots,
        records,
    )


def verify_malicious_sql(section, capture, shots, records) -> None:
    half = shots[0].half
    run_id = section.trigger("verify-malicious-sql").run_ids[0]
    run, problems = section.api.wait(run_id, lambda r: manifest.malicious_sql(r, half))
    capture.wait_text("Defense layers")
    time.sleep(PAGE_SETTLE)
    _take(capture, shots, records, "stopped", run, problems)


def verify_retry_cap(section, capture, shots, records) -> None:
    run_id = section.trigger("verify-retry-cap").run_ids[0]
    if shots[0].half == "planted":
        # The moment is the run still going past the cap; then wait for its end, so it does not
        # run on into the next scenario's reset.
        run, problems = section.api.wait(run_id, manifest.retry_cap_climbing, RETRY_TIMEOUT)
        if not problems:
            capture.wait_text("Checklist, attempt")
            time.sleep(PAGE_SETTLE)
        _take(capture, shots, records, "climbing", run, problems)
        section.api.wait(run_id, finished, RETRY_TIMEOUT)
        return
    run, problems = section.api.wait(run_id, manifest.retry_cap_escalated)
    if not problems:
        capture.wait_text("Stopped at the cap")
    time.sleep(PAGE_SETTLE)
    _take(capture, shots, records, "escalated", run, problems)


def events_webhook_question(section, capture, shots, records) -> None:
    run_id = section.trigger("events-webhook-question").run_ids[0]
    run, problems = section.api.wait(run_id, manifest.webhook_question)
    capture.wait_selector(strip_in("done", run_id))
    time.sleep(PAGE_SETTLE)
    _take(capture, shots, records, "posted", run, problems)


def events_approval_survives_restart(section, capture, shots, records) -> None:
    run_id = section.trigger("events-approval-survives-restart").run_ids[0]
    run, problems = section.api.wait(run_id, manifest.holding)
    if problems:
        _take(capture, shots, records, "held", run, problems)
        return
    capture.wait_selector(strip_in("holding", run_id))
    time.sleep(PAGE_SETTLE)
    _take(capture, shots, records, "held", run, [])
    # The person's step: Restart worker on the page itself (POST /control/restart-worker); the
    # line saying what the restart did belongs to the page that pressed the button.
    capture.page.get_by_role("button", name="Restart worker").click()
    time.sleep(section.args.restart_wait)
    run = section.api.run(run_id)
    problems = manifest.holding(run)
    if shots[0].half == "planted":
        # The in-memory checkpointer: the record still says holding (it is in Postgres), so the
        # loss shows when the run is approved and no checkpoint is there to resume.
        if not problems:
            run = _approve_until_done(section, run_id)
            problems = manifest.approval_lost(run)
        if not problems:
            capture.wait_text("The pending approval was lost")
        time.sleep(PAGE_SETTLE)
        _take(capture, shots, records, "lost", run, problems)
        return
    capture.wait_text("The pending approval survived")
    time.sleep(PAGE_SETTLE)
    _take(capture, shots, records, "after-restart", run, problems)
    if problems:
        return
    if any(s.moment == "review" for s in shots):
        _review_dialog(section, shots, records, run)
    run = _approve_until_done(section, run_id)
    problems = manifest.posted(run)
    capture.wait_text("moved on after the restart")
    time.sleep(PAGE_SETTLE)
    _take(capture, shots, records, "approved", run, problems)


def _review_dialog(section: Section, shots, records, run: dict[str, Any]) -> None:
    """Review on the held strip, in a page of its own, so the page that pressed Restart worker
    keeps its line about the restart. The dialog is closed by closing that page: nothing decided."""
    run_id = str(run["run_id"])
    dialog = Capture(section.browser, section.console, "events")
    try:
        problems: list[str] = []
        dialog.page.locator(f'button[data-review="{run_id}"]').first.click(timeout=30_000)
        if not dialog.wait_selector('[role="dialog"]') or not dialog.wait_text("Why it holds"):
            problems = ["the Review dialog did not open with its reason"]
        time.sleep(PAGE_SETTLE)
        _take(dialog, shots, records, "review", run, problems)
    finally:
        dialog.close()


def _approve_until_done(section: Section, run_id: str) -> dict[str, Any]:
    """Approve as the dialog's Approve and run does, again for each query the reviewer's changes
    bring (an approved query is never asked about twice), until the run has finished."""
    from datapilot.contracts.api import ApprovalIn

    body = ApprovalIn(decision="approve", decided_by="console").model_dump(mode="json")
    deadline = time.monotonic() + RUN_TIMEOUT
    run = section.api.run(run_id)
    while time.monotonic() < deadline:
        run = section.api.run(run_id)
        if run["status"] in manifest.FINISHED - {"awaiting_approval"}:
            break
        if run["status"] == "awaiting_approval" and manifest.open_approvals(run):
            section.api.post(f"/approvals/{run_id}", json=body).raise_for_status()
        time.sleep(3)
    return run


def events_duplicate_events(section, capture, shots, records) -> None:
    run_id = section.trigger("events-duplicate-events").run_ids[0]
    run, problems = section.api.wait(run_id, manifest.posted)
    planted = shots[0].half == "planted"
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:  # fixed: the digest, sent twice, posts once
        session_runs = section.api.json("/runs", params={"limit": 200})["runs"]
        run = section.api.run(run_id)
        check = manifest.duplicates_repeated if planted else manifest.duplicate_events
        problems = check(run, session_runs)
        if not problems:
            break
        time.sleep(3)
    if planted:
        same = [r for r in session_runs if r.get("question") == run.get("question")]
        if not problems:
            for other in same:
                capture.wait_selector(strip_in("done", str(other["run_id"])))
        time.sleep(PAGE_SETTLE)
        _take(capture, shots, records, "posted-three", run, problems)
        for record in records.values():
            record.run_ids = sorted({*record.run_ids, *(str(r["run_id"]) for r in same)})
        return
    capture.wait_text("2 duplicates absorbed")
    time.sleep(PAGE_SETTLE)
    _take(capture, shots, records, "posted", run, problems)


def events_kill_switch_in_flight(section, capture, shots, records) -> None:
    # The demo sends the webhook question, waits until it runs, then arms and engages the kill
    # switch through POST /control/kill-switch, as the status line's two clicks do.
    run_id = section.trigger("events-kill-switch-in-flight").run_ids[0]
    if shots[0].half == "planted":
        # At claim only: the switch, engaged while the run is in flight, never reaches it.
        run, _ = section.api.wait(run_id, finished)
        problems = manifest.kill_switch_ignored(run, section.api.json("/control"))
        lane = "holding" if run["status"] == "awaiting_approval" else "done"
        if not problems:
            capture.wait_selector(strip_in(lane, run_id))
        time.sleep(PAGE_SETTLE)
        _take(capture, shots, records, "kept-going", run, problems)
        return
    if any(s.moment == "engaged-running" for s in shots):
        control = section.api.json("/control")
        run = section.api.run(run_id)
        problems = manifest.kill_switch_engaged_running(run, control)
        if not problems and not capture.wait_selector(strip_in("running", run_id), timeout=5):
            problems = ["the page did not show the run in the Running lane in time"]
        _take(capture, shots, records, "engaged-running", run, problems)
    run, _ = section.api.wait(run_id, finished)
    problems = manifest.kill_switch_stopped(run, section.api.json("/control"))
    capture.wait_selector(strip_in("blocked_killswitch", run_id))
    time.sleep(PAGE_SETTLE)
    _take(capture, shots, records, "stopped", run, problems)


SCENARIOS: dict[str, Callable[..., None]] = {
    "agent-simple-question": agent_simple_question,
    "agent-confident-wrong-answer": agent_confident_wrong_answer,
    "agent-unbounded-rows": agent_unbounded_rows,
    "verify-malicious-sql": verify_malicious_sql,
    "verify-retry-cap": verify_retry_cap,
    "verify-graders-pass-still-wrong": verify_graders_pass_still_wrong,
    "events-webhook-question": events_webhook_question,
    "events-approval-survives-restart": events_approval_survives_restart,
    "events-duplicate-events": events_duplicate_events,
    "events-kill-switch-in-flight": events_kill_switch_in_flight,
}


# --- the planted flags, read from the api -----------------------------------------------------
def stack_flags(api: Api, section_slug: str) -> tuple[list[str], str | None]:
    """The planted flags the stack has on, from the zero-token probe's run record once it has
    finished: the api's, and the worker's, which it adds as it takes the run (so a worker still
    running with a flag, after a failed restart back, never passes as clean). The record is
    cleared by the section's reset that follows. Also the active knowledge version, read from ops
    as the reset reports it (the probe is a defense check, which answers under no version)."""
    from datapilot import db
    from datapilot.config import active_pack
    from datapilot.loop3_events import commands

    run_id = commands.demo(manifest.FLAG_PROBE_DEMO, client=api).run_ids[0]
    run, problems = api.wait(run_id, finished, 60)
    if problems:  # never taken: the worker's flags are not in the record yet
        raise RuntimeError(f"the flag probe's run {run_id} did not finish: {'; '.join(problems)}")
    commands.reset(section_slug)
    with db.connect(db.Role.APP) as conn:
        row = conn.execute(
            "SELECT version FROM ops.knowledge_versions WHERE pack = %s AND status = 'active'",
            (active_pack(),),
        ).fetchone()
    return list(run.get("planted_active") or []), row and row["version"]


def wanted(args: argparse.Namespace) -> tuple[list[Shot], list[tuple[Shot, str]]]:
    """The section's shots to take now, and the ones left for another half or chain step."""
    take, left = [], []
    for shot in manifest.shots_for(args.section):
        if args.only and shot.name not in args.only:
            continue
        if args.chain_step and shot.chain_step != args.chain_step:
            continue
        if shot.half != args.half or shot.paced != args.paced:
            pacing = " --paced" if shot.paced else ""
            left.append((shot, f"needs --half {shot.half}{pacing}"))
            continue
        take.append(shot)
    return take, left


def expected_for(shots: list[Shot]) -> set[str]:
    """The flags the shots' demo switches on for its own runs (one scenario's shots); SystemExit
    when they need different sets, which are taken one run of this runner each."""
    from datapilot.contracts import registries

    demos = registries.demos()
    groups: dict[frozenset[str], list[str]] = {}
    for shot in shots:
        flags = frozenset(manifest.expected_flags(shot, demos.by_id(shot.scenario).planted))
        groups.setdefault(flags, []).append(shot.name)
    if len(groups) > 1:
        lines = [
            f"  {manifest.half_command(set(flags))}: "
            + " ".join(f"--only {name}" for name in names)
            for flags, names in groups.items()
        ]
        raise SystemExit(
            "x the chosen images need different flags for a demo's runs; take each set in its "
            "own run:\n"
            + "\n".join(lines)
        )
    return set(next(iter(groups), frozenset()))


# --- Section 4: the chain steps -----------------------------------------------------------------
CHAIN_PAGE_TEXT = {
    "baseline-running": "Not run yet",
    "baseline-done": None,
    "naive-analyzer-blocked": "Gate: blocked.",
    "analyzer-team": "Knowledge diff, active version to",
    "candidate-done": "Gate: ready for human approval.",
    "promoted": "is the active version, promoted from",
    "finale": "Gold check passed",
}


def run_chain_step(args: argparse.Namespace, api: Api, browser: Any, shots: list[Shot]) -> list:
    step = args.chain_step
    records = {
        s.name: Record(s.name, list(s.paths), s.scenario, s.moment, attempt=1) for s in shots
    }
    deadline = time.monotonic() + args.chain_timeout
    while True:
        requests = api.json("/improvement/requests")["requests"]
        problems = manifest.chain_state(step, requests)
        if not problems or time.monotonic() > deadline:
            break
        time.sleep(5)
    request_ids = [r["request_id"] for r in requests[:4]]
    if step == "naive-analyzer-blocked" and not problems:
        flags = manifest.newest(requests, "analyzer").get("result", {}).get("planted_active", [])
        print(f"  the naive analyzer ran with {flags}")
    run: dict[str, Any] = {}
    if step == "finale" and not problems:
        runs = api.json("/runs", params={"limit": 50})["runs"]
        sent = [r for r in runs if r.get("demo_name") == "improve-cleared-unattended"]
        run = api.run(sent[0]["run_id"]) if sent else {}
        problems = manifest.posted(run) if run else ["no finale run in this session"]
    for page in dict.fromkeys(s.page for s in shots):
        capture = Capture(browser, args.console.rstrip("/"), page)
        try:
            text = CHAIN_PAGE_TEXT[step]
            if text and not problems and not capture.wait_text(text, timeout=120):
                problems = [*problems, f"the page does not show {text!r}"]
            time.sleep(PAGE_SETTLE)
            for shot in (s for s in shots if s.page == page):
                record = records[shot.name]
                record.request_ids = request_ids
                if run:
                    record.run_ids, record.facts = [str(run["run_id"])], manifest.facts(run)
                record.problems = list(problems)
                if not problems:
                    capture.shoot(shot, record, str(run["run_id"]) if run else None)
        finally:
            capture.close()
    return list(records.values())


# --- the command ---------------------------------------------------------------------------------
def parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("section", choices=sorted(manifest.SECTION_FOLDERS))
    parser.add_argument("--only", action="append", default=[], help="one image name (repeat)")
    parser.add_argument("--half", choices=manifest.HALVES, default="fixed")
    parser.add_argument(
        "--paced", action="store_true", help="the paced images: demo pacing on for the demo's runs"
    )
    parser.add_argument("--chain-step", choices=manifest.CHAIN_STEPS, default=None)
    parser.add_argument("--attempts", type=int, default=2, help="triggers per scenario at most")
    parser.add_argument("--restart-wait", type=float, default=30.0, help="seconds after a restart")
    parser.add_argument("--chain-timeout", type=float, default=CHAIN_TIMEOUT)
    parser.add_argument("--api", default=None, help="the api (default: DATAPILOT_API_URL)")
    parser.add_argument("--console", default="http://localhost:8501")
    parser.add_argument("--log", type=Path, default=None, help="the JSON log to write")
    parser.add_argument("--dry-run", action="store_true", help="list the plan; call nothing")
    args = parser.parse_args(argv)
    hill = args.section == "hill-climbing-loop"
    if hill and not args.chain_step:
        steps = ", ".join(manifest.CHAIN_STEPS)
        parser.error(f"Section 4 captures one chain step at a time: --chain-step, one of {steps}")
    if args.chain_step and not hill:
        parser.error("--chain-step is for hill-climbing-loop only")
    unknown = set(args.only) - {s.name for s in manifest.shots_for(args.section)}
    if unknown:
        parser.error(f"not an image of {args.section}: {', '.join(sorted(unknown))}")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse(sys.argv[1:] if argv is None else argv)
    shots, left = wanted(args)
    for shot, why in left:
        print(f"  later: {shot.name} ({why})")
    if not shots:
        print("x no image of this section matches; see the later list above")
        return 2
    print(f"{args.section}: {len(shots)} images; the stack must have every planted flag off")
    for name, group in manifest.scenarios(shots):
        needed = manifest.half_command(expected_for(group))
        print(f"  {name} ({needed}): {', '.join(s.name for s in group)}")
    if args.dry_run:
        return 0

    from playwright.sync_api import sync_playwright

    from datapilot.settings import get_settings

    api = Api(args.api or get_settings().datapilot_api_url)
    log_path = args.log or LOG_FOLDER / f"{args.section}-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    log: dict[str, Any] = {
        "section": args.section,
        "started_at": now(),
        "half": args.half,
        "paced": args.paced,
        "chain_step": args.chain_step,
        "records": [],
    }
    records: list[Record] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            if args.chain_step:
                records = run_chain_step(args, api, browser, shots)
            else:
                found, version = stack_flags(api, args.section)
                log["stack_flags"], log["knowledge_version"] = found, version
                # both halves need a clean stack: the planted half's flags go with its own runs
                problem = manifest.flags_problem(set(), found) or manifest.version_problem(
                    args.section, version
                )
                if problem:
                    print(
                        f"x the stack is not in the section's starting state: {problem}. Turn "
                        "every planted flag off (set it to 0 in .env, then make up): the planted "
                        "half switches its flags on for its own runs, as make demo NAME=<demo> "
                        "PLANTED=1 does; for the knowledge version, make reset "
                        "NAME=hill-climbing-loop."
                    )
                    log["refused"] = problem
                    return 2
                section = Section(args, api, browser)
                for name, group in manifest.scenarios(shots):
                    records += section.run_scenario(name, group)
                if args.section == "event-loop":
                    section.reset()  # the kill switch released, so nothing later is blocked
        finally:
            browser.close()
            log["finished_at"] = now()
            log["records"] = [asdict(r) for r in records]
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(json.dumps(log, indent=2, default=str) + "\n", encoding="utf-8")
            print(f"log: {log_path}")
    failed = [r for r in records if not r.written]
    for record in failed:
        print(f"x {record.shot}: {'; '.join(record.problems) or 'not taken'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
