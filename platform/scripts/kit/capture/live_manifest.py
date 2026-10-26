"""The live console captures of the course: which image shows which state, and how to tell that the
state is there. Pure data and pure functions: no network, no browser, no database.

Every image in section-*/demo/expected/ is a live capture listed here once (docs/images/ holds
copies of some, listed as `copies`). live_captures.py reads this manifest: for each image of a
section it resets the section, triggers the registry demo that produces the state, waits for the
state in the run's own record through the api, frames the element named here, and writes the PNG.
Section 4's images come from the hill-climbing chain, which the lead drives; for them the runner
only waits for the chain step's state and captures it (`chain_step`), triggering nothing.

The state checks take the api's replies (contracts.api RunDetail, ImprovementRequestOut, and
ControlState, as dicts) and return the problems found: an empty list means the state is there.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

SECTION_FOLDERS = {
    "agent-loop": "section-1-agent-loop",
    "verification-loop": "section-2-verification-loop",
    "event-loop": "section-3-event-loop",
    "hill-climbing-loop": "section-4-hill-climbing-loop",
}
PAGES = ("agent", "verify", "events", "improve")
# The console's default page is served at its root: Streamlit ignores the url_path of the page
# marked default=True (platform/console/app.py), so /agent opens a "Page not found" dialog over the
# Agent page. Every Agent page image of 24 October 2026 shows that dialog; this sends it to /.
DEFAULT_PAGE = "agent"
HALVES = ("fixed", "planted")
FINISHED = {
    "posted",
    "answered",
    "escalated",
    "failed",
    "rejected",
    "awaiting_approval",
    "blocked_killswitch",
    "blocked_budget",
}
# The zero-token demo the runner sends first to read the stack's planted flags from the api: the
# run's planted_active is what the api process has switched on (contracts.api RunSummary).
FLAG_PROBE_DEMO = "verify-malicious-sql"
PACING = "DEMO_PACING"

# Frames: Playwright selectors (they reach into the components' open shadow roots).
STATUS_LINE = ".sl"
SQL = ".asql"
LEDGER = ".ledger .stamps"
DIFF = '[data-testid="stHeading"]:has-text("Knowledge diff, active version to")'
GATE = 'p:has-text("Gate:")'
DEFENSE = 'p:has-text("Defense layers")'
TOOL_CALLS = 'p:has-text("Tool calls")'
CHECKLIST = 'p:has-text("Checklist, attempt")'
STOPPED_AT_CAP = 'p:has-text("Stopped at the cap")'
RUN_TOKENS = 'p:has-text("Tokens for this run")'
# The Verify page's row of buttons (Streamlit marks a keyed widget's container st-key-<key>). A run
# with no defense layers, gold check, or reviewer leaves the page's right column empty, so a frame
# from the checklist down is blank from the middle to the right edge: 1,058 of 2,560 columns on
# 25 October, over the image check's quarter. The row of buttons reaches about three quarters of
# the width (Send cartesian query ends near column 1,920), so a frame that starts at the row keeps
# the blank band under a quarter with the checklist, the cap line, and the tokens line below it.
VERIFY_BUTTONS = ".st-key-verify-malicious"
LAST_VERIFY_BUTTON = ".st-key-verify-cartesian"
CHANNEL = '[data-testid="stHeading"]:has-text("Channel")'
# The newest post's text: the Channel lists posts newest first, each body as one st.text.
NEWEST_POST = '[data-testid="stText"]'
RESTART_LINE = 'p:has-text("Worker restart requested.")'
ANSWER = 'p:has-text("Answer against gold")'
GOLD = '[data-testid="stMarkdownContainer"]:has-text("Gold answer")'
# The run's summary line at the end of the Agent and Verify pages ("18,778 tokens, $0.0017").
TOKENS_LINE = 'p:has-text("tokens, $")'
DIALOG = '[role="dialog"]'
# The end of the page's last element with a height (capture kit framing.PAGE_END).
PAGE_END = "page-end"


def strip(part: str = "") -> str:
    """The run's own strip on the run board (`{run}` is filled with the run id), or a part of it."""
    return f'article.strip[data-run="{{run}}"] {part}'.strip()


@dataclass(frozen=True)
class Shot:
    name: str  # the file name without .png, in the section's demo/expected/ folder
    section: str  # section slug
    scenario: str  # the registry demo that produces the state, or the chain step's name
    moment: str  # the state within the scenario at which the image is taken
    page: str  # the console page: agent, verify, events, improve
    caption: str  # what the page's caption must make the reader notice
    alt: str  # what the image shows, for its alt text
    top: str | None = None  # placed under the fixed header; None (and no bottom): the page's top
    bottom: str | None = None  # its end placed at the bottom of the viewport
    copies: tuple[str, ...] = ()  # more repository paths that hold the same image
    half: str = "fixed"  # the planted half the state needs: fixed (no flag) or planted
    paced: bool = False  # demo pacing on (DEMO_PACING=1)
    chain_step: str | None = None  # Section 4: the chain step whose state this is
    # The planted half's code flags, when the guide plants fewer than the demo's registry entry
    # lists (None: every code flag the demo plants)
    flags: tuple[str, ...] | None = None
    owner_fix: str = ""  # the fix the owner asked for, when the image had a fault
    # What carries the moment: each selector's first match must be wholly in the frame (inside
    # the viewport under the header, and inside any list that scrolls it) or nothing is written.
    # `{run}` is the run's id.
    must_see: tuple[str, ...] = ()
    # The moment is a dialog (Review): the runner refuses every other image with a dialog in view.
    dialog: bool = False

    def seen(self, run_id: str | None) -> tuple[str, ...]:
        """must_see with the run's id filled in."""
        return tuple(s.replace("{run}", run_id or "") for s in self.must_see)

    @property
    def path(self) -> str:
        return f"{SECTION_FOLDERS[self.section]}/demo/expected/{self.name}.png"

    @property
    def paths(self) -> tuple[str, ...]:
        return (self.path, *self.copies)


def page_path(page: str) -> str:
    """The console path of a page: the default page is the root."""
    return "" if page == DEFAULT_PAGE else page


def _docs(name: str) -> tuple[str, ...]:
    return (f"docs/images/{name}.png",)


SHOTS: tuple[Shot, ...] = (
    # --- Section 1: Agent loop ------------------------------------------------------------
    Shot(
        "agent-simple-question-answer",
        "agent-loop",
        "agent-simple-question",
        "answered",
        "agent",
        "The analyst lists the tables, describes one, and runs one query; the answer comes with "
        "its query and the live stamp of this run: its start time and its trace link.",
        "The Agent page after the simple question: its tool calls list_tables, describe_table, "
        "and run_query, the live stamp with its start time and trace link, the query, and the "
        "answer",
        top=TOOL_CALLS,
        copies=_docs("agent-simple-question-answer"),
        owner_fix=(
            "the live stamp in view (the setup pages show this image); no Page not found dialog"
        ),
        must_see=(TOOL_CALLS, f"{SQL} .head"),
    ),
    Shot(
        "agent-confident-wrong-answer-run",
        "agent-loop",
        "agent-confident-wrong-answer",
        "answered",
        "agent",
        "Under the starting knowledge the analyst answers the spine question with a number, "
        "however it hedges; the status line under the question says whether the run posted or "
        "holds for a person's approval.",
        "The Agent page after the spine question: the run's status, its tool calls, the live "
        "stamp, and the start of the annotated query",
        must_see=(STATUS_LINE,),
    ),
    Shot(
        "agent-confident-wrong-answer-sql",
        "agent-loop",
        "agent-confident-wrong-answer",
        "answered",
        "agent",
        "Every trap note has its number on a fragment of the query; the answer does not match "
        "gold. Any status filter the query has (such as status = 4) is named in the text.",
        "The annotated query from its live stamp down: numbered marks on the fragments behind each "
        "trap note, the notes, the agent's answer, and the gold check",
        top=SQL,
        copies=_docs("agent-confident-wrong-answer-sql"),
        owner_fix=(
            "every trap note has a mark in the query (the fiscal-year mark was missing); a "
            "status = 4 filter is marked or explained; the hedged answer is described as it "
            "appears; no clipped top"
        ),
        must_see=(f"{SQL} .head", f"{SQL} .code"),
    ),
    Shot(
        "agent-confident-wrong-answer-gold",
        "agent-loop",
        "agent-confident-wrong-answer",
        "answered",
        "agent",
        "The gold check fails on both warehouse and warehouse_alt: the agent's value against the "
        "gold value.",
        "The answer against gold: the agent's value, the gold value, and the mismatch on both "
        "databases",
        bottom=GOLD,
        must_see=(ANSWER, GOLD),
    ),
    Shot(
        "agent-unbounded-rows-planted-tokens",
        "agent-loop",
        "agent-unbounded-rows",
        "finished",
        "agent",
        "With the unbounded rows bug on, every row of the 10,000-row query reaches the model: the "
        "tokens line at the bottom reads more than 100,000 tokens for one run.",
        "The Agent page after the large query with the unbounded rows bug on: the run's status, "
        "its answer, and the tokens line with more than 100,000 tokens",
        bottom=PAGE_END,
        half="planted",
        must_see=(TOKENS_LINE,),
    ),
    Shot(
        "agent-unbounded-rows-fixed-tokens",
        "agent-loop",
        "agent-unbounded-rows",
        "finished",
        "agent",
        "With the row cap, the same steps stay small: the tokens line reads under 60,000 tokens. "
        "The truncation notice and the total count are in the run_query result, in the trace.",
        "The Agent page after the large query with the row cap: the run's status, its answer, and "
        "the tokens line with under 60,000 tokens",
        bottom=PAGE_END,
        must_see=(TOKENS_LINE,),
    ),
    # --- Section 2: Verification loop -----------------------------------------------------
    Shot(
        "verify-malicious-sql-layers",
        "verification-loop",
        "verify-malicious-sql",
        "stopped",
        "verify",
        "With the fixed system the syntax-tree guard stops two statements before they run, and "
        "the role's grants stop the raw DELETE with SQLSTATE 42501.",
        "The Verify page's defense layers for three statements: the guard stops the stacked "
        "statements and the data-modifying CTE, and the role grants stop the raw DELETE",
        top=DEFENSE,
        copies=_docs("verify-malicious-sql-layers"),
        must_see=(DEFENSE,),
    ),
    Shot(
        "verify-malicious-sql-naive-guard-layers",
        "verification-loop",
        "verify-malicious-sql",
        "stopped",
        "verify",
        "With the naive guard planted both statements pass the guard; the read-only transaction "
        "refuses them with SQLSTATE 25006, and the grants refuse the raw DELETE with 42501.",
        "The defense layers with the naive guard planted: two statements pass the guard and the "
        "read-only transaction stops them, then the role grants stop the raw DELETE",
        top=DEFENSE,
        half="planted",
        must_see=(DEFENSE,),
    ),
    Shot(
        "verify-retry-cap-escalated",
        "verification-loop",
        "verify-retry-cap",
        "escalated",
        "verify",
        "The injected grader fails every attempt; the cap stops the run after attempt 3 of 3 and it "
        "ends escalated, with the tokens it spent against the cap per run.",
        "The Verify page after the retry cap demo: the checklist on attempt 3 of 3 with the "
        "injected grader failed, the line Stopped at the cap: escalated, and the tokens line",
        top=VERIFY_BUTTONS,
        must_see=(VERIFY_BUTTONS, LAST_VERIFY_BUTTON, CHECKLIST, STOPPED_AT_CAP, RUN_TOKENS),
    ),
    Shot(
        "verify-retry-cap-no-cap-climbing",
        "verification-loop",
        "verify-retry-cap",
        "climbing",
        "verify",
        "With the missing retry cap the run is past attempt 3 and still going; the tokens line "
        "keeps climbing toward the cap of 60,000 tokens per run.",
        "The Verify page with the missing retry cap planted: the checklist past attempt 3, the run "
        "still verifying, and the tokens bar climbing",
        top=VERIFY_BUTTONS,
        half="planted",
        must_see=(VERIFY_BUTTONS, LAST_VERIFY_BUTTON, CHECKLIST, RUN_TOKENS),
    ),
    Shot(
        "verify-graders-pass-still-wrong-checklist",
        "verification-loop",
        "verify-graders-pass-still-wrong",
        "answered",
        "verify",
        "Every grader passes on the run's last attempt while the gold check fails on both "
        "databases; the reviewer's verdict is beside it, whichever way it went.",
        "The Verify page after the spine question: the checklist with every grader passed, the "
        "answer against gold with a mismatch on both databases, and the reviewer's verdict",
        copies=_docs("verify-graders-pass-still-wrong-checklist"),
        must_see=('p:has-text("Checklist, attempt")',),
    ),
    Shot(
        "verify-graders-pass-still-wrong-sql",
        "verification-loop",
        "verify-graders-pass-still-wrong",
        "answered",
        "verify",
        "The query that passed every grader, with its trap notes, each numbered on a fragment.",
        "The annotated query below the checklist, with its trap notes, each numbered on a "
        "fragment of the query",
        bottom=SQL,
        owner_fix="every trap note has a mark in the query",
        must_see=(f"{SQL} .code", f"{SQL} .notes"),
    ),
    # --- Section 3: Event loop ------------------------------------------------------------
    Shot(
        "events-webhook-question-board",
        "event-loop",
        "events-webhook-question",
        "posted",
        "events",
        "The webhook question becomes an event and a job and moves to Done at the report-only "
        "level.",
        "The Events page: the status line at the report-only level and the run board with the "
        "webhook question posted in Done",
        must_see=(strip(),),
    ),
    Shot(
        "events-webhook-question-channel",
        "event-loop",
        "events-webhook-question",
        "posted",
        "events",
        "At the report-only level the answer is posted labelled unverified.",
        "The Channel with one post, posted at the report-only level and labelled unverified",
        top=CHANNEL,
        copies=_docs("events-webhook-question-channel"),
        owner_fix="no clipped top (the earlier capture cut the Done and Review strips)",
        must_see=(CHANNEL, NEWEST_POST),
    ),
    Shot(
        "events-approval-held",
        "event-loop",
        "events-approval-survives-restart",
        "held",
        "events",
        "The California marketing export reads personal data, so the run holds for a person's "
        "approval before its query runs.",
        "The run board with the California export holding for approval, with its Review button",
        must_see=(strip("button.review"),),
    ),
    Shot(
        "events-approval-after-restart",
        "event-loop",
        "events-approval-survives-restart",
        "after-restart",
        "events",
        "The worker restarts and the Postgres checkpointer keeps the pending approval: the run is "
        "still holding.",
        "After Restart worker: the line that the pending approval survived and the run is still "
        "holding, above the Channel",
        top=RESTART_LINE,
        copies=_docs("events-approval-after-restart"),
        owner_fix="no clipped top",
        must_see=(RESTART_LINE, CHANNEL),
    ),
    Shot(
        "events-approval-review-dialog",
        "event-loop",
        "events-approval-survives-restart",
        "review",
        "events",
        "Before anything runs, the dialog states the exact query, about how many rows it returns, "
        "and why it holds: the query reads personal data.",
        "The Review dialog, Approve this export?, with the row estimate, the reason it holds, the "
        "exact query, and the Approve and run and Reject buttons",
        must_see=(DIALOG,),
        dialog=True,
    ),
    Shot(
        "events-approval-approved-posted",
        "event-loop",
        "events-approval-survives-restart",
        "approved",
        "events",
        "Approving resumes the run after the restart, and the export is posted.",
        "After approval: the line that the run moved on after the restart, and the export posted "
        "in the Channel",
        top=RESTART_LINE,
        must_see=(RESTART_LINE, NEWEST_POST),
    ),
    Shot(
        "events-approval-lost-after-restart",
        "event-loop",
        "events-approval-survives-restart",
        "lost",
        "events",
        "With the in-memory checkpointer the record still says holding after the restart, but the "
        "checkpoint died with the worker: approving fails the run, and the pending approval is "
        "lost.",
        "After Restart worker and approval with the in-memory checkpointer planted: the line that "
        "the pending approval was lost and the run failed, above a Channel with no export",
        top=RESTART_LINE,
        half="planted",
        must_see=(RESTART_LINE,),
    ),
    Shot(
        "events-duplicate-events-board",
        "event-loop",
        "events-duplicate-events",
        "posted",
        "events",
        "The same event three times: one run, one post, and 2 duplicates absorbed; the digest "
        "sent twice runs once.",
        "The run board with one posted question marked 2 duplicates absorbed, and one digest",
        copies=_docs("events-duplicate-events-board"),
        must_see=(strip(".dups"),),
    ),
    Shot(
        "events-duplicate-events-no-idempotency-channel",
        "event-loop",
        "events-duplicate-events",
        "posted-three",
        "events",
        "Three posts of the same answer in the Channel: the effect happened once per delivery.",
        "The Channel with the missing idempotency planted: the same answer posted three times",
        top=CHANNEL,
        half="planted",
        flags=("BUG_NO_IDEMPOTENCY",),
        must_see=(CHANNEL, NEWEST_POST),
    ),
    Shot(
        "events-kill-switch-in-flight-board",
        "event-loop",
        "events-kill-switch-in-flight",
        "stopped",
        "events",
        "The kill switch stops the run in flight and drops the system to the report-only level.",
        "The status line forced to the report-only level by the kill switch, and the run under "
        "Blocked by kill switch",
        copies=_docs("events-kill-switch-in-flight-board"),
        must_see=(strip(),),
    ),
    Shot(
        "events-kill-switch-paced-running",
        "event-loop",
        "events-kill-switch-in-flight",
        "engaged-running",
        "events",
        "With demo pacing on, the run is visibly in flight when the kill switch is engaged.",
        "With demo pacing on: the status line forced to the report-only level by the kill switch, "
        "a pacing chip, and the run still in the Running lane",
        paced=True,
        must_see=(strip(),),
    ),
    Shot(
        "events-kill-switch-paced-stopped",
        "event-loop",
        "events-kill-switch-in-flight",
        "stopped",
        "events",
        "It stops at its next step and moves off the board to Blocked by kill switch.",
        "With demo pacing on: the Running lane empty and the run under Blocked by kill switch",
        paced=True,
        must_see=(strip(),),
    ),
    Shot(
        "events-kill-switch-at-claim-only-board",
        "event-loop",
        "events-kill-switch-in-flight",
        "kept-going",
        "events",
        "With the kill switch checked at claim only, the run in flight never sees it: the status "
        "line says the switch is engaged, and the run still finished on the board.",
        "With the kill switch at claim only and demo pacing on: the status line with the kill "
        "switch engaged at the report-only level, and the run finished on the board, not blocked",
        half="planted",
        paced=True,
        must_see=(strip(),),
    ),
    # --- Section 4: Hill-climbing loop (the chain; the runner triggers nothing) -------------
    Shot(
        "improve-baseline-experiment-running",
        "hill-climbing-loop",
        "improve-baseline-experiment",
        "running",
        "improve",
        "The baseline benchmark starts under v1: the ledger fills in as each item's runs finish.",
        "The Improve page at the start of the baseline experiment: the baseline stamp and the "
        "holdout items marked Not run yet",
        chain_step="baseline-running",
        must_see=(LEDGER,),
    ),
    Shot(
        "improve-baseline-experiment-ledger",
        "hill-climbing-loop",
        "improve-baseline-experiment",
        "done",
        "improve",
        "Under the starting knowledge v1 few holdout items pass; the trap items fail.",
        "The finished baseline ledger under v1, each row passed or failed with its runs, some "
        "with a Trace link and some Not traced",
        top=LEDGER,
        chain_step="baseline-done",
        must_see=(LEDGER,),
    ),
    Shot(
        "improve-naive-analyzer-blocked-guard",
        "hill-climbing-loop",
        "improve-naive-analyzer-blocked",
        "analyzed",
        "improve",
        "The naive analyzer writes one rule per failed dev item; the overfit guard flags every "
        "one, and its verdict is not applied.",
        "The Improve page after the naive analyzer: the knowledge diff under the line that the "
        "overfit guard flags every rule, not applied",
        top=DIFF,
        half="planted",
        chain_step="naive-analyzer-blocked",
        must_see=(DIFF,),
    ),
    Shot(
        "improve-naive-analyzer-blocked-gate",
        "hill-climbing-loop",
        "improve-naive-analyzer-blocked",
        "blocked",
        "improve",
        "The gate blocks the naive candidate: every rule it adds fails the overfit guard, "
        "whatever its holdout count.",
        "The candidate ledger, then the gate's verdict: blocked, naming the rules the overfit "
        "guard rejects",
        bottom=GATE,
        half="planted",
        chain_step="naive-analyzer-blocked",
        must_see=(GATE,),
    ),
    Shot(
        "improve-analyzer-team-diff",
        "hill-climbing-loop",
        "improve-analyzer-team-approve",
        "analyzed",
        "improve",
        "The analyzer team writes two candidates, runs each on the dev split only, and keeps one; "
        "the diff shows its general rules for human approval.",
        "The knowledge diff from the active version to the candidate, under the line naming both "
        "candidates and the one kept",
        top=DIFF,
        chain_step="analyzer-team",
        must_see=(DIFF,),
    ),
    Shot(
        "improve-candidate-experiment-ledger",
        "hill-climbing-loop",
        "improve-candidate-experiment",
        "done",
        "improve",
        "The candidate flips holdout trap items against this session's baseline, with no "
        "regressions.",
        "The holdout ledger comparing v1 and the candidate: rows marked Fixed: now passes or No "
        "change, and no regression",
        top=LEDGER,
        copies=_docs("improve-candidate-experiment-ledger"),
        chain_step="candidate-done",
        must_see=(LEDGER,),
    ),
    Shot(
        "improve-candidate-experiment-gate",
        "hill-climbing-loop",
        "improve-candidate-experiment",
        "done",
        "improve",
        "The gate is ready for human approval: more holdout passes and no regressions on either "
        "split.",
        "The gate's verdict, ready for human approval, above the controls and the knowledge diff",
        top=GATE,
        chain_step="candidate-done",
        must_see=(GATE,),
    ),
    Shot(
        "improve-promotion-cleared",
        "hill-climbing-loop",
        "improve-candidate-experiment",
        "promoted",
        "improve",
        "After approval the gate promotes the candidate; a family is cleared for the unattended "
        "level when every one of its holdout items passes on the confirmed standard.",
        "The status line after the promotion with the families cleared and not cleared, and the "
        "ledger reading Replaced, v1 and Active",
        copies=_docs("improve-promotion-cleared"),
        chain_step="promoted",
        must_see=(STATUS_LINE, LEDGER),
    ),
    Shot(
        "improve-cleared-unattended-board",
        "hill-climbing-loop",
        "improve-cleared-unattended",
        "posted",
        "events",
        "The spine question arrives as a webhook under the new active version and posts at the "
        "level its family earned; its strip shows the gold check.",
        "The Events page at the unattended level with the cleared families, and the spine "
        "question in Done with its gold check",
        chain_step="finale",
        must_see=(strip(".gold"),),
    ),
    Shot(
        "improve-cleared-unattended-channel",
        "hill-climbing-loop",
        "improve-cleared-unattended",
        "posted",
        "events",
        "The answer matches gold and posts at the unattended level, without approval.",
        "The Channel post of the spine question's answer, posted at the unattended level",
        top=CHANNEL,
        copies=_docs("improve-cleared-unattended-channel"),
        chain_step="finale",
        must_see=(CHANNEL, NEWEST_POST),
    ),
)
CHAIN_STEPS = tuple(dict.fromkeys(s.chain_step for s in SHOTS if s.chain_step))
# Listed and embedded in the guide, not captured yet: the lead's live captures write them. A test
# keeps this list honest: an image here must not exist yet, and every other listed image must.
AWAITING_CAPTURE: frozenset[str] = frozenset()


def shots_for(section: str) -> list[Shot]:
    return [shot for shot in SHOTS if shot.section == section]


def scenarios(shots: Iterable[Shot]) -> list[tuple[str, list[Shot]]]:
    """The shots grouped by the scenario that produces them, in manifest order: one trigger each."""
    grouped: dict[tuple[str, str, bool], list[Shot]] = {}
    for shot in shots:
        grouped.setdefault((shot.scenario, shot.half, shot.paced), []).append(shot)
    return [(key[0], found) for key, found in grouped.items()]


# --- planted flags ----------------------------------------------------------------------------
def code_flags(planted: Iterable[str]) -> set[str]:
    """The planted items that are flags (code bugs and demo pacing), which a demo switches on for
    its own runs, as against data conditions and pre-authored knowledge."""
    return {item for item in planted if item.startswith("BUG_") or item == PACING}


def expected_flags(shot: Shot, demo_planted: Iterable[str]) -> set[str]:
    """The flags that must be on, and only those, for the shot's half: none for the fixed half;
    the demo's code bugs for the planted half (or the shot's own `flags`, when the guide plants
    fewer); demo pacing on top when the shot is paced."""
    bugs = {flag for flag in code_flags(demo_planted) if flag != PACING}
    if shot.flags is not None:
        bugs = set(shot.flags)
    flags = bugs if shot.half == "planted" else set()
    return flags | {PACING} if shot.paced else flags


STARTING_VERSION = "v1"  # Sections 1 to 3 are taught under the starting knowledge


def version_problem(section: str, version: str | None) -> str | None:
    """None when the section's images may be taken under `version`, else what differs. Sections 1
    to 3 show the starting knowledge v1; a version promoted in Section 4 answers differently (a
    rule changes the count), so their images would show rules a learner has not met yet."""
    if section == "hill-climbing-loop" or version == STARTING_VERSION:
        return None
    return f"the active knowledge version is {version}, not {STARTING_VERSION}"


def flags_problem(expected: set[str], found: Iterable[str]) -> str | None:
    """None when the stack's flags are exactly the expected ones, else what differs."""
    on = set(found)
    if on == expected:
        return None
    parts = []
    if expected - on:
        parts.append(f"off but needed: {', '.join(sorted(expected - on))}")
    if on - expected:
        parts.append(f"on but not wanted: {', '.join(sorted(on - expected))}")
    return "; ".join(parts)


def half_command(expected: set[str]) -> str:
    """What the half switches on for its demo's own runs (as make demo NAME=<demo> PLANTED=1 does,
    in the header of the demo's events); the stack itself keeps every flag off."""
    if not expected:
        return "no planted flag"
    return " and ".join(sorted(expected)) + " on for the demo's own runs only"


# --- the run's own record ---------------------------------------------------------------------
def envelope(run: Mapping[str, Any]) -> dict[str, Any]:
    return dict((run.get("answer") or {}).get("envelope") or {})


def tools(run: Mapping[str, Any]) -> list[str]:
    return [
        str(e["payload"].get("tool"))
        for e in run.get("events", [])
        if e["kind"] == "tool_call_finished"
    ]


def tokens(run: Mapping[str, Any]) -> int:
    return int(run.get("tokens_in") or 0) + int(run.get("tokens_out") or 0)


def attempts(run: Mapping[str, Any]) -> int:
    """How many times the run went to its graders: each attempt enters verifying once."""
    return sum(
        1
        for e in run.get("events", [])
        if e["kind"] == "status_changed" and e["payload"].get("to") == "verifying"
    )


def gold(run: Mapping[str, Any]) -> dict[str, Any] | None:
    found = [e["payload"] for e in run.get("events", []) if e["payload"].get("grader") == "gold"]
    return found[-1] if found else None


def defense(run: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(layer, reason) of each statement's stopping layer, in order."""
    return [
        (str(e["payload"]["grader"]).removeprefix("defense: "), str(e["payload"].get("reason")))
        for e in run.get("events", [])
        if str(e["payload"].get("grader", "")).startswith("defense:")
    ]


def last_attempt_graders(run: Mapping[str, Any]) -> list[dict[str, Any]]:
    graders = [
        e["payload"]
        for e in run.get("events", [])
        if e["kind"] == "grader_result"
        and e["payload"].get("grader") != "gold"
        and not str(e["payload"].get("grader", "")).startswith("defense")
    ]
    newest = max((int(g.get("attempt") or 1) for g in graders), default=1)
    return [g for g in graders if int(g.get("attempt") or 1) == newest]


def reviewer(run: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [e["payload"] for e in run.get("events", []) if e["kind"] == "reviewer_verdict"]


def open_approvals(run: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [a for a in run.get("approvals", []) if a.get("decision") is None]


def blocked_in_flight(run: Mapping[str, Any]) -> bool:
    return any(
        e["kind"] == "killswitch_blocked" and e["payload"].get("at") == "in flight"
        for e in run.get("events", [])
    )


_STATUS_FILTER = re.compile(r"(?i)\bstatus\s*(?:=|<>|!=|\bin\b|\bnot\s+in\b)\s*\(?\s*[\d, ]+\)?")


def status_filters(sql: str) -> list[str]:
    """Each filter on the opaque status code in a query, as written (status = 4, status <> 5)."""
    return [" ".join(hit.group(0).split()) for hit in _STATUS_FILTER.finditer(sql or "")]


def facts(run: Mapping[str, Any]) -> dict[str, Any]:
    """What a caption may need from the run, for the capture log: the answer as written (with any
    hedge), the query's status filters, the gold check, and the reviewer's verdicts."""
    answer = envelope(run)
    check = gold(run)
    return {
        "run_id": run.get("run_id"),
        "status": run.get("status"),
        "started_at": run.get("started_at"),
        "question": run.get("question"),
        "answer_text": answer.get("answer_text"),
        "final_sql": answer.get("final_sql"),
        "status_filters": status_filters(str(answer.get("final_sql") or "")),
        "agent_value": check and check.get("agent_value"),
        "gold_value": check and check.get("gold_value"),
        "gold_passed": check and check.get("passed"),
        "trap_labels": check and check.get("trap_labels"),
        "reviewer": [(v.get("outcome"), v.get("reasons")) for v in reviewer(run)],
        "tools": tools(run),
        "defense": defense(run),
        "tokens": tokens(run),
        "attempts": attempts(run),
        "cost_usd": run.get("cost_usd"),
        "planted_active": run.get("planted_active"),
        "autonomy_level_applied": run.get("autonomy_level_applied"),
        "knowledge_version": run.get("knowledge_version"),
        "duplicates_ignored": run.get("duplicates_ignored"),
        "posts": [
            (post.get("label"), (post.get("body") or {}).get("text"))
            for post in run.get("posts", [])
        ],
    }


# --- the frame: [] when it may be written --------------------------------------------------------
def frame_problems(
    *,
    blockers: Sequence[str],
    edges_clean: bool,
    edges: Mapping[str, Any],
    missing: Sequence[str],
    image_check: Sequence[str],
    hidden: Sequence[str] = (),
) -> list[str]:
    """Why a frame may not be written: something lies over the page (a dialog, an error box), an
    edge cuts text, the moment is not wholly in the frame, the moment has no box on the page at
    all (no scroll can show it: a run board lane shows its newest strips only, then "N more"), or
    the image check reports it."""
    problems = [f"in view: {b}" for b in blockers]
    if not edges_clean:
        problems.append(f"an edge cuts content in every frame tried ({dict(edges)})")
    problems += [f"not wholly in the frame: {selector}" for selector in missing]
    problems += [
        f"hidden on the page, so no frame can show it (a lane's strips past its limit are "
        f"counted under N more): {selector}"
        for selector in hidden
    ]
    problems += [f"image check: {problem}" for problem in image_check]
    return problems


# --- the state checks: [] when the state is there ----------------------------------------------
def simple_question(run: Mapping[str, Any]) -> list[str]:
    problems = []
    if run.get("status") != "posted":
        problems.append(f"the run is {run.get('status')}, not posted")
    if "run_query" not in tools(run):
        problems.append("no run_query call")
    if not envelope(run).get("final_sql"):
        problems.append("no query in the answer")
    return problems


def confident_wrong_answer(run: Mapping[str, Any]) -> list[str]:
    """Finished, with a query and a failed gold check that names at least one trap (the registry's
    can-vary list: a run with no number gets no gold check, so the class resets and asks again)."""
    problems = []
    if run.get("status") not in ("posted", "awaiting_approval"):
        problems.append(f"the run is {run.get('status')}, not posted or holding for approval")
    if not envelope(run).get("final_sql"):
        problems.append("no query in the answer")
    check = gold(run)
    if check is None:
        problems.append("no gold check (the answer gave no number)")
    elif check.get("passed"):
        problems.append("the gold check passed")
    elif not check.get("trap_labels"):
        problems.append("the gold check names no trap")
    return problems


# The token lines the unbounded rows demo is measured by (calibration: 17,298 to 26,683 tokens
# with the row cap, 183,639 to 186,689 with the bug on; docs/calibration-report.md).
UNBOUNDED_ABOVE = 100_000
CAPPED_BELOW = 60_000
MAX_ATTEMPTS = 3  # limits.max_retries in platform/packs/datapilot_us/pack.yaml


def unbounded_rows(run: Mapping[str, Any], half: str) -> list[str]:
    """Finished, with the tokens of its half: far above the bound with the bug, under it without."""
    if run.get("status") not in FINISHED:
        return [f"the run is {run.get('status')}"]
    used = tokens(run)
    if half == "planted" and used <= UNBOUNDED_ABOVE:
        return [f"{used:,} tokens with the bug on, expected more than {UNBOUNDED_ABOVE:,}"]
    if half == "fixed" and used >= CAPPED_BELOW:
        return [f"{used:,} tokens with the row cap, expected under {CAPPED_BELOW:,}"]
    return []


def retry_cap_escalated(run: Mapping[str, Any]) -> list[str]:
    problems = []
    if run.get("status") != "escalated":
        problems.append(f"the run is {run.get('status')}, not escalated")
    if attempts(run) != MAX_ATTEMPTS:
        problems.append(f"{attempts(run)} attempts, expected {MAX_ATTEMPTS}")
    return problems


def retry_cap_climbing(run: Mapping[str, Any]) -> list[str]:
    """Still going past the cap: the missing retry cap's moment, taken while the run works."""
    problems = []
    if run.get("status") in FINISHED:
        problems.append(f"the run is {run.get('status')}, no longer going")
    if attempts(run) <= MAX_ATTEMPTS:
        problems.append(f"{attempts(run)} attempts, not past the cap of {MAX_ATTEMPTS} yet")
    return problems


def malicious_sql(run: Mapping[str, Any], half: str) -> list[str]:
    layers = defense(run)
    names = [layer for layer, _ in layers]
    if half == "planted":
        expected = ["read-only transaction", "read-only transaction", "role grants"]
        codes_ok = len(layers) == 3 and all("25006" in r for _, r in layers[:2])
    else:
        expected = ["guard: parse", "guard: statement_policy", "role grants"]
        codes_ok = len(layers) == 3
    problems = []
    if names != expected:
        problems.append(f"stopped by {names}, expected {expected}")
    elif not codes_ok or "42501" not in layers[2][1]:
        problems.append(f"the refusals do not carry the expected SQLSTATE codes: {layers}")
    return problems


def graders_pass_still_wrong(run: Mapping[str, Any]) -> list[str]:
    problems = []
    if run.get("status") not in FINISHED:
        problems.append(f"the run is {run.get('status')}")
    latest = last_attempt_graders(run)
    if not latest or not all(g.get("passed") for g in latest):
        problems.append("not every grader of the last attempt passed")
    check = gold(run)
    if check is None:
        problems.append("no gold check")
    elif check.get("passed"):
        problems.append("the gold check passed")
    return problems


def webhook_question(run: Mapping[str, Any]) -> list[str]:
    labels = [p.get("label") for p in run.get("posts", [])]
    problems = []
    if run.get("status") != "posted":
        problems.append(f"the run is {run.get('status')}, not posted")
    if labels != ["unverified"]:
        problems.append(f"posts labelled {labels}, expected one unverified post")
    return problems


def holding(run: Mapping[str, Any]) -> list[str]:
    if run.get("status") != "awaiting_approval":
        return [f"the run is {run.get('status')}, not holding for approval"]
    if not open_approvals(run):
        return ["no approval is open"]
    return []


def posted(run: Mapping[str, Any]) -> list[str]:
    return [] if run.get("status") == "posted" else [f"the run is {run.get('status')}, not posted"]


def approval_lost(run: Mapping[str, Any]) -> list[str]:
    """Approved after a restart with the in-memory checkpointer: no checkpoint holds the run, so
    the resume fails it (loop2_verification.loop: "the pending approval was lost")."""
    if run.get("status") != "failed":
        return [f"the run is {run.get('status')}, not failed by the lost approval"]
    return []


def duplicates_repeated(
    run: Mapping[str, Any], session_runs: Sequence[Mapping[str, Any]]
) -> list[str]:
    """The missing idempotency: three runs of the same question, each posted."""
    same = [r for r in session_runs if r.get("question") == run.get("question")]
    problems = []
    if len(same) != 3:
        problems.append(f"{len(same)} runs of the question, expected 3")
    unposted = [r.get("status") for r in same if r.get("status") != "posted"]
    if unposted:
        problems.append(f"runs of the question not posted: {unposted}")
    return problems


def duplicate_events(
    run: Mapping[str, Any], session_runs: Sequence[Mapping[str, Any]]
) -> list[str]:
    problems = posted(run)
    if run.get("duplicates_ignored") != 2:
        problems.append(f"{run.get('duplicates_ignored')} duplicates absorbed, expected 2")
    same = [r for r in session_runs if r.get("question") == run.get("question")]
    digests = [r for r in session_runs if r.get("question") != run.get("question")]
    if len(same) != 1:
        problems.append(f"{len(same)} runs of the question, expected 1")
    if len(digests) != 1 or digests[0].get("status") != "posted":
        problems.append(f"{len(digests)} digest runs, expected one posted")
    return problems


def kill_switch_stopped(run: Mapping[str, Any], control: Mapping[str, Any]) -> list[str]:
    problems = []
    if run.get("status") != "blocked_killswitch":
        problems.append(f"the run is {run.get('status')}, not blocked by the kill switch")
    elif not blocked_in_flight(run):
        problems.append("the run was blocked at claim, not in flight")
    if control.get("autonomy_level") != "report_only":
        problems.append(f"the level is {control.get('autonomy_level')}, not report-only")
    return problems


def kill_switch_ignored(run: Mapping[str, Any], control: Mapping[str, Any]) -> list[str]:
    """The kill switch at claim only: engaged while the run was in flight, and the run finished
    anyway (posted, or holding for a reviewer's concern), never blocked."""
    problems = []
    if control.get("kill_switch") != "engaged":
        problems.append(f"the kill switch is {control.get('kill_switch')}")
    if run.get("status") not in ("posted", "awaiting_approval"):
        problems.append(f"the run is {run.get('status')}, not finished past the switch")
    if any(e["kind"] == "killswitch_blocked" for e in run.get("events", [])):
        problems.append("the kill switch blocked the run")
    return problems


def kill_switch_engaged_running(run: Mapping[str, Any], control: Mapping[str, Any]) -> list[str]:
    problems = []
    if control.get("kill_switch") != "engaged":
        problems.append(f"the kill switch is {control.get('kill_switch')}")
    if run.get("status") not in ("running", "verifying"):
        problems.append(f"the run is {run.get('status')}, no longer in flight")
    return problems


# --- Section 4: the chain's improvement requests ----------------------------------------------
def newest(requests: Sequence[Mapping[str, Any]], kind: str, **params: Any) -> dict[str, Any]:
    """The newest request of a kind (the api lists them newest first), matching `params`."""
    for request in requests:
        if request.get("kind") != kind:
            continue
        if all((request.get("params") or {}).get(k) == v for k, v in params.items()):
            return dict(request)
    return {}


def chain_state(step: str, requests: Sequence[Mapping[str, Any]]) -> list[str]:
    """[] when the chain step's requests are in the state its images show."""
    experiment = newest(requests, "experiment")
    analyzer = newest(requests, "analyzer")
    candidate = newest(requests, "experiment", target="candidate")
    result = dict(candidate.get("result") or {})
    analyzed = dict(analyzer.get("result") or {})
    planted = "BUG_NAIVE_ANALYZER" in (analyzed.get("planted_active") or [])
    if step == "baseline-running":
        return [] if experiment.get("status") == "running" else ["no experiment is running"]
    if step == "baseline-done":
        if experiment.get("status") != "done" or (experiment.get("params") or {}).get(
            "target"
        ) not in (None, "active"):
            return ["the newest experiment is not a finished one on the active version"]
        return []
    if step == "naive-analyzer-blocked":
        problems = []
        if analyzer.get("status") != "done" or not planted:
            problems.append("no finished naive analyzer request (BUG_NAIVE_ANALYZER)")
        if candidate.get("status") != "done" or result.get("verdict") != "blocked":
            problems.append("no finished candidate experiment with a blocked verdict")
        return problems
    if step == "analyzer-team":
        if analyzer.get("status") != "done" or planted:
            return ["no finished analyzer team request"]
        return []
    if step == "candidate-done":
        if candidate.get("status") != "done" or not result.get("ready_for_approval"):
            return ["no finished candidate experiment ready for approval"]
        return []
    if step in ("promoted", "finale"):
        running = [r for r in requests if r.get("status") in ("queued", "running")]
        return [f"{len(running)} improvement requests still queued or running"] if running else []
    raise KeyError(f"unknown chain step {step!r}; the steps are {', '.join(CHAIN_STEPS)}")


@dataclass
class Record:
    """One image's line in the capture log."""

    shot: str
    paths: list[str]
    scenario: str
    moment: str
    attempt: int = 0
    written: bool = False
    problems: list[str] = field(default_factory=list)
    run_ids: list[str] = field(default_factory=list)
    request_ids: list[str] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    edges: dict[str, int] = field(default_factory=dict)
    image_check: list[str] = field(default_factory=list)
    captured_at: str | None = None
