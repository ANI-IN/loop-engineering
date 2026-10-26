"""The live capture runner, without the live stack: its manifest, its state checks, its flag check,
its argument rules, the framing measure, and the terminal renderer's cap on long lines."""

from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from datapilot.contracts import registries
from datapilot.names import SECTIONS

REPO = Path(__file__).resolve().parents[3]
KIT = REPO / "platform" / "scripts" / "kit" / "capture"
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(REPO / "platform" / "scripts"))

import framing  # noqa: E402
import live_captures  # noqa: E402
import live_manifest as manifest  # noqa: E402
import short_forms  # noqa: E402
import term_render  # noqa: E402

# The capture runner's refusals are safety tests: in make test-security's selection.
pytestmark = pytest.mark.security


def _check_images():
    spec = importlib.util.spec_from_file_location(
        "check_images", REPO / "platform" / "scripts" / "check_images.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["check_images"] = module
    spec.loader.exec_module(module)
    return module


# --- the manifest ----------------------------------------------------------------------------
def test_every_live_capture_in_the_repository_is_listed_once() -> None:
    """Terminal renders (`-terminal.png`, from term_render.py) are not console captures. An image
    awaiting its first live capture is listed and embedded, and must not exist yet: once the lead
    captures it, it leaves manifest.AWAITING_CAPTURE."""
    on_disk = {
        p.relative_to(REPO).as_posix()
        for pattern in ("section-*/demo/expected/*.png", "docs/images/*.png")
        for p in REPO.glob(pattern)
        if not p.name.endswith("-terminal.png")
    }
    listed = [path for shot in manifest.SHOTS for path in shot.paths]
    assert len(listed) == len(set(listed)), "an image is listed twice"
    awaiting = {p for s in manifest.SHOTS if s.name in manifest.AWAITING_CAPTURE for p in s.paths}
    assert not manifest.AWAITING_CAPTURE - {s.name for s in manifest.SHOTS}
    assert set(listed) - awaiting == on_disk
    assert not awaiting & on_disk, "a captured image is still marked as awaiting its capture"


def _page_texts() -> str:
    pages = ["guide", "setup", "section-1-agent-loop", "section-2-verification-loop"]
    pages += ["section-3-event-loop", "section-4-hill-climbing-loop", "docs"]
    return "\n".join(
        p.read_text(encoding="utf-8") for folder in pages for p in (REPO / folder).rglob("*.md")
    )


AWAITING_MARK = "check-style: allow SC06 awaiting its live capture"


def test_every_image_awaiting_its_capture_is_embedded_already() -> None:
    """The guide embeds the path the manifest writes, so the page is right once it is captured.
    Each such embed carries the style check's allow marker for the missing file, and only those:
    a captured image leaves AWAITING_CAPTURE and its marker goes with it."""
    lines = _page_texts().splitlines()
    awaiting = [s.path for s in manifest.SHOTS if s.name in manifest.AWAITING_CAPTURE]
    for path in awaiting:
        embeds = [line for line in lines if line.startswith("![") and f"{path})" in line]
        assert embeds, path
        assert all(AWAITING_MARK in line for line in embeds), path
    for line in lines:
        if AWAITING_MARK in line:
            assert any(f"{path})" in line for path in awaiting), line


def test_the_agent_page_is_opened_at_the_console_root() -> None:
    """Streamlit serves the default page at /; /agent showed a Page not found dialog over every
    Agent page image of 24 October 2026."""
    assert manifest.page_path("agent") == ""
    assert manifest.page_path("events") == "events"
    app = (REPO / "platform" / "console" / "app.py").read_text(encoding="utf-8")
    assert f'url_path="{manifest.DEFAULT_PAGE}", default=True' in app


def test_section_folders_are_the_course_sections() -> None:
    assert {s.slug: s.folder for s in SECTIONS} == manifest.SECTION_FOLDERS


def test_each_shot_comes_from_a_registry_demo_of_its_section() -> None:
    demos = registries.demos()
    for shot in manifest.SHOTS:
        assert demos.by_id(shot.scenario).section == shot.section, shot.name
        assert shot.page in manifest.PAGES and shot.half in manifest.HALVES


def test_a_planted_or_paced_shot_needs_flags_its_demo_plants() -> None:
    demos = registries.demos()
    for shot in manifest.SHOTS:
        planted = demos.by_id(shot.scenario).planted
        flags = manifest.expected_flags(shot, planted)
        if shot.half == "planted":
            assert flags - {manifest.PACING}, f"{shot.name}: its demo plants no code bug"
        if shot.paced:
            assert manifest.PACING in flags and manifest.PACING in planted, shot.name
        if shot.half == "fixed" and not shot.paced:
            assert flags == set(), shot.name


def test_section_four_shots_are_chain_steps_and_the_rest_are_triggered() -> None:
    for shot in manifest.SHOTS:
        if shot.section == "hill-climbing-loop":
            assert shot.chain_step in manifest.CHAIN_STEPS, shot.name
        else:
            assert shot.chain_step is None and shot.scenario in live_captures.SCENARIOS, shot.name
    assert set(live_captures.CHAIN_PAGE_TEXT) == set(manifest.CHAIN_STEPS)


def test_one_scenario_shares_one_page() -> None:
    for _name, group in manifest.scenarios(s for s in manifest.SHOTS if not s.chain_step):
        assert len({s.page for s in group}) == 1


def test_captions_and_alt_texts_are_plain_words() -> None:
    for shot in manifest.SHOTS:
        for text in (shot.caption, shot.alt):
            assert text.strip() and not text.lower().startswith(("image", "screenshot"))
            assert short_forms.find(text) == [], (shot.name, text)
            assert short_forms.find_shorthand(text) == [], (shot.name, text)


# --- the planted flags -------------------------------------------------------------------------
def test_flags_must_match_exactly() -> None:
    assert manifest.flags_problem({"BUG_NAIVE_GUARD"}, ["BUG_NAIVE_GUARD"]) is None
    assert manifest.flags_problem(set(), []) is None
    assert manifest.flags_problem(set(), ["DEMO_PACING"]) == "on but not wanted: DEMO_PACING"
    missing = manifest.flags_problem({"BUG_NAIVE_GUARD"}, ["BUG_NO_RETRY_CAP"])
    assert missing == "off but needed: BUG_NAIVE_GUARD; on but not wanted: BUG_NO_RETRY_CAP"


def test_sections_one_to_three_are_taken_only_under_the_starting_knowledge() -> None:
    """Live, 24 October: a capture run after the safeguard step ran under v11, and the simple
    question counted 374,538 eligible orders instead of v1's figure; every image was retaken."""
    assert manifest.version_problem("agent-loop", "v1") is None
    assert "v11, not v1" in (manifest.version_problem("event-loop", "v11") or "")
    assert manifest.version_problem("verification-loop", None)
    assert manifest.version_problem("hill-climbing-loop", "v11") is None


def test_the_half_command_names_every_flag() -> None:
    """Since 26 October the flags go with the demo's own runs, never into .env."""
    assert manifest.half_command(set()) == "no planted flag"
    assert manifest.half_command({"DEMO_PACING", "BUG_KILLSWITCH_AT_CLAIM_ONLY"}) == (
        "BUG_KILLSWITCH_AT_CLAIM_ONLY and DEMO_PACING on for the demo's own runs only"
    )
    assert ".env" not in manifest.half_command({"DEMO_PACING"})


def test_the_planted_naive_guard_image_needs_only_the_naive_guard() -> None:
    shot = next(s for s in manifest.SHOTS if s.name == "verify-malicious-sql-naive-guard-layers")
    planted = registries.demos().by_id(shot.scenario).planted
    assert manifest.expected_flags(shot, planted) == {"BUG_NAIVE_GUARD"}


# --- the state checks --------------------------------------------------------------------------
def _event(kind: str, **payload: object) -> dict:
    return {"kind": kind, "payload": payload}


def _run(status: str = "posted", **extra: object) -> dict:
    return {"run_id": "r1", "status": status, "events": [], "approvals": [], "posts": [], **extra}


def test_the_simple_question_needs_a_query_and_a_post() -> None:
    run = _run(
        events=[_event("tool_call_finished", tool="run_query")],
        answer={"envelope": {"final_sql": "SELECT count(*) FROM orders"}},
    )
    assert manifest.simple_question(run) == []
    assert manifest.simple_question(_run("escalated")) == [
        "the run is escalated, not posted",
        "no run_query call",
        "no query in the answer",
    ]


def test_the_confident_wrong_answer_needs_a_failed_gold_check_with_a_trap() -> None:
    sql = {"answer": {"envelope": {"final_sql": "SELECT 1"}}}
    wrong = _event("grader_result", grader="gold", passed=False, trap_labels=["utc_truncation"])
    assert manifest.confident_wrong_answer(_run("awaiting_approval", events=[wrong], **sql)) == []
    assert manifest.confident_wrong_answer(_run(**sql)) == [
        "no gold check (the answer gave no number)"
    ]
    right = _event("grader_result", grader="gold", passed=True, trap_labels=[])
    assert manifest.confident_wrong_answer(_run(events=[right], **sql)) == ["the gold check passed"]


def test_the_malicious_sql_layers_depend_on_the_half() -> None:
    def layers(*found: tuple[str, str]) -> dict:
        events = [_event("grader_result", grader=f"defense: {g}", reason=r) for g, r in found]
        return _run(events=events)

    fixed = layers(
        ("guard: parse", "two statements"),
        ("guard: statement_policy", "a data-modifying CTE"),
        ("role grants", "42501"),
    )
    naive = layers(
        ("read-only transaction", "25006"),
        ("read-only transaction", "25006"),
        ("role grants", "42501"),
    )
    assert manifest.malicious_sql(fixed, "fixed") == []
    assert manifest.malicious_sql(naive, "planted") == []
    assert manifest.malicious_sql(naive, "fixed") != []


def test_duplicate_events_need_one_run_one_digest_and_two_absorbed() -> None:
    run = _run(question="How many orders?", duplicates_ignored=2)
    digest = {"question": "Digest", "status": "posted"}
    assert manifest.duplicate_events(run, [run, digest]) == []
    assert manifest.duplicate_events(run, [run, run, digest, digest]) == [
        "2 runs of the question, expected 1",
        "2 digest runs, expected one posted",
    ]


def test_the_kill_switch_must_stop_the_run_in_flight() -> None:
    control = {"autonomy_level": "report_only", "kill_switch": "engaged"}
    at_claim = _run("blocked_killswitch", events=[_event("killswitch_blocked", at="claim")])
    in_flight = _run("blocked_killswitch", events=[_event("killswitch_blocked", at="in flight")])
    assert manifest.kill_switch_stopped(in_flight, control) == []
    assert manifest.kill_switch_stopped(at_claim, control) == [
        "the run was blocked at claim, not in flight"
    ]
    assert manifest.kill_switch_engaged_running(_run("running"), control) == []


def test_unbounded_rows_are_read_by_the_tokens_of_each_half() -> None:
    assert manifest.unbounded_rows(_run(tokens_in=180_000, tokens_out=5_000), "planted") == []
    assert manifest.unbounded_rows(_run(tokens_in=20_000, tokens_out=1_000), "fixed") == []
    assert manifest.unbounded_rows(_run(tokens_in=20_000), "planted") == [
        "20,000 tokens with the bug on, expected more than 100,000"
    ]
    assert manifest.unbounded_rows(_run(tokens_in=70_000), "fixed") == [
        "70,000 tokens with the row cap, expected under 60,000"
    ]
    assert manifest.unbounded_rows(_run("running", tokens_in=1), "fixed") == ["the run is running"]


def _verifying(times: int) -> list[dict]:
    return [_event("status_changed", to="verifying") for _ in range(times)]


def test_the_retry_cap_escalates_at_three_and_the_missing_cap_keeps_going() -> None:
    assert manifest.retry_cap_escalated(_run("escalated", events=_verifying(3))) == []
    assert manifest.retry_cap_escalated(_run("escalated", events=_verifying(2))) == [
        "2 attempts, expected 3"
    ]
    assert manifest.retry_cap_climbing(_run("verifying", events=_verifying(4))) == []
    assert manifest.retry_cap_climbing(_run("running", events=_verifying(3))) == [
        "3 attempts, not past the cap of 3 yet"
    ]
    assert manifest.retry_cap_climbing(_run("escalated", events=_verifying(5))) == [
        "the run is escalated, no longer going"
    ]


def test_the_lost_approval_fails_the_run_when_approved() -> None:
    assert manifest.approval_lost(_run("failed")) == []
    assert manifest.approval_lost(_run("posted")) == [
        "the run is posted, not failed by the lost approval"
    ]


def test_missing_idempotency_needs_three_posted_runs_of_the_question() -> None:
    run = _run(question="How many orders?")
    assert manifest.duplicates_repeated(run, [run, run, run]) == []
    assert manifest.duplicates_repeated(run, [run]) == ["1 runs of the question, expected 3"]
    held = {**run, "status": "awaiting_approval"}
    assert manifest.duplicates_repeated(run, [run, run, held]) == [
        "runs of the question not posted: ['awaiting_approval']"
    ]


def test_the_kill_switch_at_claim_only_lets_the_run_finish() -> None:
    engaged = {"kill_switch": "engaged", "autonomy_level": "report_only"}
    assert manifest.kill_switch_ignored(_run("posted"), engaged) == []
    blocked = _run("blocked_killswitch", events=[_event("killswitch_blocked", at="in flight")])
    assert manifest.kill_switch_ignored(blocked, engaged) == [
        "the run is blocked_killswitch, not finished past the switch",
        "the kill switch blocked the run",
    ]
    assert manifest.kill_switch_ignored(_run("posted"), {"kill_switch": "released"}) == [
        "the kill switch is released"
    ]


def test_the_webhook_question_posts_once_unverified() -> None:
    run = _run(posts=[{"label": "unverified"}])
    assert manifest.webhook_question(run) == []
    assert manifest.webhook_question(_run(posts=[])) == [
        "posts labelled [], expected one unverified post"
    ]


@pytest.mark.parametrize(
    ("sql", "found"),
    [
        ("WHERE o.status = 4 AND x", ["status = 4"]),
        ("where status<>5", ["status<>5"]),
        ("AND o.status IN (3, 4)", ["status IN (3, 4)"]),
        ("SELECT status FROM orders", []),
    ],
)
def test_status_filters_are_found_for_the_caption(sql: str, found: list[str]) -> None:
    assert manifest.status_filters(sql) == found


def test_chain_states_read_the_newest_requests() -> None:
    naive = {
        "kind": "analyzer",
        "status": "done",
        "params": {},
        "result": {"planted_active": ["BUG_NAIVE_ANALYZER"]},
    }
    blocked = {
        "kind": "experiment",
        "status": "done",
        "params": {"target": "candidate"},
        "result": {"verdict": "blocked"},
    }
    baseline = {"kind": "experiment", "status": "done", "params": {"target": "active"}}
    assert manifest.chain_state("naive-analyzer-blocked", [blocked, naive, baseline]) == []
    assert manifest.chain_state("analyzer-team", [blocked, naive]) == [
        "no finished analyzer team request"
    ]
    assert manifest.chain_state("baseline-done", [baseline]) == []
    assert manifest.chain_state("baseline-running", [baseline]) == ["no experiment is running"]
    assert manifest.chain_state("finale", [{**baseline, "status": "running"}]) == [
        "1 improvement requests still queued or running"
    ]
    with pytest.raises(KeyError):
        manifest.chain_state("no-such-step", [])


# --- the command's rules ----------------------------------------------------------------------
def test_section_four_needs_a_chain_step_and_only_section_four_takes_one() -> None:
    with pytest.raises(SystemExit):
        live_captures.parse(["hill-climbing-loop"])
    with pytest.raises(SystemExit):
        live_captures.parse(["agent-loop", "--chain-step", "finale"])
    with pytest.raises(SystemExit):
        live_captures.parse(["agent-loop", "--only", "events-approval-held"])
    args = live_captures.parse(["hill-climbing-loop", "--chain-step", "candidate-done"])
    assert [s.name for s in live_captures.wanted(args)[0]] == [
        "improve-candidate-experiment-ledger",
        "improve-candidate-experiment-gate",
    ]


def test_a_planted_image_waits_for_the_planted_half() -> None:
    """Section 2 has two planted images since the retry cap's was added, each with its own flag:
    the lead takes each with --only on its own stack."""
    fixed = live_captures.parse(["verification-loop"])
    take, left = live_captures.wanted(fixed)
    assert "verify-malicious-sql-naive-guard-layers" not in [s.name for s in take]
    assert ("verify-malicious-sql-naive-guard-layers", "needs --half planted") in [
        (s.name, why) for s, why in left
    ]
    planted = live_captures.parse(["verification-loop", "--half", "planted"])
    assert [s.name for s in live_captures.wanted(planted)[0]] == [
        "verify-malicious-sql-naive-guard-layers",
        "verify-retry-cap-no-cap-climbing",
    ]
    with pytest.raises(SystemExit) as refused:
        live_captures.expected_for(live_captures.wanted(planted)[0])
    assert (
        "BUG_NAIVE_GUARD on for the demo's own runs only: --only verify-malicious-sql-naive"
        in str(refused.value)
    )
    one = live_captures.parse(
        ["verification-loop", "--half", "planted", "--only", "verify-retry-cap-no-cap-climbing"]
    )
    assert live_captures.expected_for(live_captures.wanted(one)[0]) == {"BUG_NO_RETRY_CAP"}


@pytest.mark.parametrize(
    ("name", "flags"),
    [
        ("agent-unbounded-rows-planted-tokens", {"BUG_UNBOUNDED_ROWS"}),
        ("agent-unbounded-rows-fixed-tokens", set()),
        ("verify-retry-cap-escalated", set()),
        ("events-approval-review-dialog", set()),
        ("events-approval-lost-after-restart", {"BUG_MEMORY_CHECKPOINTER"}),
        ("events-duplicate-events-no-idempotency-channel", {"BUG_NO_IDEMPOTENCY"}),
        ("events-kill-switch-at-claim-only-board", {"BUG_KILLSWITCH_AT_CLAIM_ONLY", "DEMO_PACING"}),
    ],
)
def test_each_guide_image_needs_the_flags_its_guide_step_sets(name: str, flags: set[str]) -> None:
    """The guide's steps set one flag at a time; step 8 of the event loop chapter sets only the
    missing idempotency, though its demo also lists the random digest id."""
    shot = next(s for s in manifest.SHOTS if s.name == name)
    planted = registries.demos().by_id(shot.scenario).planted
    assert manifest.expected_flags(shot, planted) == flags


def test_paced_images_wait_for_demo_pacing() -> None:
    paced = live_captures.parse(["event-loop", "--paced"])
    assert [s.name for s in live_captures.wanted(paced)[0]] == [
        "events-kill-switch-paced-running",
        "events-kill-switch-paced-stopped",
    ]
    assert live_captures.expected_for(live_captures.wanted(paced)[0]) == {"DEMO_PACING"}


def test_a_dry_run_lists_the_plan_and_calls_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    assert live_captures.main(["agent-loop", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "agent-loop: 5 images; the stack must have every planted flag off" in out
    assert "  agent-unbounded-rows (no planted flag): " in out


# --- the planted half: the demo's own runs, through make demo's path ---------------------------
class _ProbeApi:
    """The api as stack_flags sees it: the probe's run is queued at first, and the worker adds
    its own flag to the record only when it takes the run."""

    def __init__(self) -> None:
        self.reads = 0

    def post(self, path: str, **kwargs: object) -> object:
        return _JsonResponse({"run_id": "probe"})

    def get(self, path: str, **kwargs: object) -> object:
        return _JsonResponse(self.run("probe"))

    def run(self, run_id: str) -> dict:
        self.reads += 1
        if self.reads == 1:
            return {"run_id": run_id, "status": "queued", "planted_active": []}
        return {"run_id": run_id, "status": "posted", "planted_active": ["BUG_LOCK_DURING_LLM"]}

    def wait(self, run_id: str, check, timeout: float = 0) -> tuple[dict, list[str]]:
        while True:
            found = self.run(run_id)
            if not check(found):
                return found, []


class _JsonResponse:
    status_code = 200  # a live session is open (GET /sessions/current answers)

    def __init__(self, body: dict) -> None:
        self.body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.body


def test_the_flag_probe_reads_the_run_after_the_worker_took_it(monkeypatch) -> None:
    """The security review of 26 October: the record read before the run finished missed a
    worker still running with a flag, so the planted worker passed as the fixed half."""
    from contextlib import nullcontext
    from types import SimpleNamespace

    from datapilot import db
    from datapilot.loop3_events import commands

    monkeypatch.setattr(commands, "reset", lambda section: SimpleNamespace(lines=list))
    row = SimpleNamespace(fetchone=lambda: {"version": "v1"})
    conn = SimpleNamespace(execute=lambda *_a: row)
    monkeypatch.setattr(db, "connect", lambda *_a, **_k: nullcontext(conn))
    found, version = live_captures.stack_flags(_ProbeApi(), "event-loop")
    assert found == ["BUG_LOCK_DURING_LLM"] and version == "v1"
    assert manifest.flags_problem(set(), found) == "on but not wanted: BUG_LOCK_DURING_LLM"


def test_a_planted_half_sends_its_flags_with_the_demos_own_events(monkeypatch) -> None:
    """The capture runner plants through make demo's path (the header), never through .env."""
    from datapilot import planted

    sent: list[dict] = []

    class _Api:
        def post(self, path: str, **kwargs: object) -> object:
            sent.append(dict(kwargs.get("headers") or {}))  # type: ignore[arg-type]
            return _JsonResponse({"run_id": "r1"})

        def get(self, path: str, **kwargs: object) -> object:
            return _JsonResponse({"status": "posted"})

    args = live_captures.parse(["agent-loop", "--half", "planted"])
    section = live_captures.Section(args, _Api(), browser=None)  # type: ignore[arg-type]
    section.flags = ["BUG_UNBOUNDED_ROWS"]
    assert section.trigger("agent-unbounded-rows").run_ids == ["r1"]
    assert planted.planted("BUG_UNBOUNDED_ROWS")  # on in this process for the trigger's block
    section.demos.close()
    assert not planted.planted("BUG_UNBOUNDED_ROWS")  # and off once the attempt ends
    assert sent == [
        {
            planted.PLANTED_HEADER: "BUG_UNBOUNDED_ROWS",
            planted.DEMO_HEADER: "agent-unbounded-rows",
        }
    ]


# --- a refused frame is never written as an image --------------------------------------------
class _ShootPage:
    """Just enough of a page for Capture.shoot: what the page's blocker script finds."""

    def __init__(self, found: list[str]) -> None:
        self.found = found

    def evaluate(self, script: str, argument: object = None) -> object:
        assert script == framing.BLOCKERS
        return list(self.found)


def _shoot(tmp_path: Path, monkeypatch, found: list[str], dialog: bool = False):
    check_images = _check_images()
    monkeypatch.setattr(check_images, "check_image", lambda *_a: [])
    monkeypatch.setattr(live_captures, "REPO", tmp_path)
    monkeypatch.setattr(live_captures, "LOG_FOLDER", tmp_path / "log")
    edges = framing.Edges(top=0, bottom=0)
    monkeypatch.setattr(framing, "framed_screenshot", lambda *_a, **_k: (b"frame", edges))
    monkeypatch.setattr(framing, "where", lambda _page, seen: dict.fromkeys(seen, framing.IN_VIEW))
    shot = manifest.Shot(
        "an-image", "event-loop", "demo", "moment", "events", "c", "a", dialog=dialog
    )
    record = manifest.Record(shot.name, list(shot.paths), shot.scenario, shot.moment)
    capture = live_captures.Capture.__new__(live_captures.Capture)
    capture.page = _ShootPage(found)
    capture.shoot(shot, record)
    return shot, record


def test_a_frame_with_a_dialog_in_view_is_never_written(tmp_path: Path, monkeypatch) -> None:
    shot, record = _shoot(tmp_path, monkeypatch, ["a dialog: Review the query"])
    assert not (tmp_path / shot.path).exists() and record.written is False
    assert record.problems == ["in view: a dialog: Review the query"]
    assert (tmp_path / "log" / "refused" / "an-image.png").read_bytes() == b"frame"


def test_a_clean_frame_is_written_and_its_trial_removed(tmp_path: Path, monkeypatch) -> None:
    shot, record = _shoot(tmp_path, monkeypatch, [])
    assert (tmp_path / shot.path).read_bytes() == b"frame"
    assert record.written is True and record.problems == [] and record.captured_at
    assert not (tmp_path / "log" / "refused" / "an-image.png").exists()


def test_a_dialog_image_allows_its_dialog_but_never_page_not_found(
    tmp_path: Path, monkeypatch
) -> None:
    page = _ShootPage(["a dialog: Why it holds", "a dialog: Page not found", "an error box: x"])
    assert framing.blockers(page, allow_dialog=True) == [
        "a dialog: Page not found",
        "an error box: x",
    ]
    assert len(framing.blockers(page)) == 3
    shot, record = _shoot(tmp_path / "review", monkeypatch, ["a dialog: Why it holds"], True)
    assert record.written is True
    lost = tmp_path / "not-found"
    shot, record = _shoot(lost, monkeypatch, ["a dialog: Page not found"], dialog=True)
    assert record.written is False and not (lost / shot.path).exists()


# --- framing: the image check's own measure ---------------------------------------------------
BACKGROUND = (236, 240, 243)


def _lines(height: int, cut_at: int | None = None) -> Image.Image:
    """A page of 'text' lines (dark strokes); with `cut_at`, one line crosses that row."""
    image = Image.new("RGB", (400, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    rows = list(range(20, height - 20, 30)) + ([cut_at - 4] if cut_at is not None else [])
    for y in rows:
        for x in range(10, 390, 8):
            draw.rectangle((x, y, x + 4, y + 10), fill=(20, 30, 40))
    return image


def test_framing_measures_edges_as_the_image_check_does() -> None:
    check_images = _check_images()
    assert framing.VISIBLE_CHANGE == check_images.VISIBLE_CHANGE
    assert framing.CLIPPED_CHANGES == check_images.CLIPPED_CHANGES
    assert framing.edges(_lines(300)).clean
    cut = _lines(300, cut_at=299)
    assert not framing.edges(cut).clean
    measured = min(check_images._changes(cut.convert("RGBA"), y) for y in (298, 299))
    assert framing.edges(cut).bottom == measured


def test_framing_sees_text_cut_under_the_fixed_header() -> None:
    image = _lines(300, cut_at=60)
    assert framing.edges(image).clean  # the image's own edges are clean
    assert not framing.edges(image, header_rows=59).clean
    boxed = Image.new("RGB", (400, 300), BACKGROUND)
    ImageDraw.Draw(boxed).rectangle((50, 40, 350, 120), outline=(20, 30, 40), width=2)
    assert framing.edges(boxed).quiet
    hidden = framing.edges(boxed, header_rows=59)  # a box's top hidden under the header
    assert hidden.clean and not hidden.quiet
    assert framing.pick_nudge([(0, framing.Edges(0, 40)), (-6, framing.Edges(0, 2))]) == -6
    assert framing.pick_nudge([(0, framing.Edges(30, 0))]) is None


def _words_cut_at_the_bottom(height: int = 300) -> Image.Image:
    """A few 'letters' (round shapes) cut by the bottom edge: fewer colour changes than the image
    check's threshold, as the cut lines of 24 October (14 to 18 changes)."""
    image = Image.new("RGB", (400, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    for x in range(20, 84, 16):
        draw.ellipse((x, height - 10, x + 10, height + 6), outline=(20, 30, 40), width=2)
    return image


def test_a_few_cut_letters_are_refused_though_the_image_check_lets_them_pass() -> None:
    check_images = _check_images()
    cut = _words_cut_at_the_bottom()
    assert check_images._clipped_edges(cut.convert("RGBA")) == []  # the image check misses it
    found = framing.edges(cut)
    assert found.bottom < framing.CLIPPED_CHANGES and found.bottom_strokes > 0
    assert not found.clean and not found.quiet


def test_box_sides_crossing_an_edge_are_clean_but_not_quiet() -> None:
    """A ledger or a diff taller than the frame: only its straight sides cross the bottom, which
    settle() takes only when no nudge ends the frame in empty page."""
    image = Image.new("RGB", (400, 300), BACKGROUND)
    draw = ImageDraw.Draw(image)
    for left in (20, 150, 280):
        draw.rectangle((left, 200, left + 100, 320), outline=(20, 30, 40), width=2)
    found = framing.edges(image)
    assert found.bottom_strokes == 0 and found.clean and not found.quiet
    assert framing.strokes([10, 12, 300, 302]) == 0  # two borders, far apart
    assert framing.strokes([10, 14, 20, 24, 30]) == 3  # the strokes of letters
    quiet = framing.Edges(0, 0)
    assert framing.pick_nudge([(0, found), (3, quiet)]) == 3  # a quiet frame first
    assert framing.pick_nudge([(0, found)]) == 0


# --- the frame's own refusals and the moment it must hold -------------------------------------
def test_a_frame_is_refused_for_a_dialog_a_cut_edge_a_missed_moment_or_the_image_check() -> None:
    edges = {"top": 0, "bottom": 16}
    assert (
        manifest.frame_problems(
            blockers=[], edges_clean=True, edges=edges, missing=[], image_check=[]
        )
        == []
    )
    found = manifest.frame_problems(
        blockers=["a dialog: Page not found"],
        edges_clean=False,
        edges=edges,
        missing=[manifest.NEWEST_POST],
        image_check=["blank area: 373 of 1440 rows are one colour"],
    )
    assert found == [
        "in view: a dialog: Page not found",
        "an edge cuts content in every frame tried ({'top': 0, 'bottom': 16})",
        f"not wholly in the frame: {manifest.NEWEST_POST}",
        "image check: blank area: 373 of 1440 rows are one colour",
    ]


def test_every_shot_names_the_moment_it_must_hold() -> None:
    for shot in manifest.SHOTS:
        assert shot.must_see, shot.name
        filled = shot.seen("run-1")
        assert all("{run}" not in s for s in filled)
        if any("data-run" in s for s in shot.must_see):  # a strip needs its run's id
            assert shot.chain_step in (None, "finale"), shot.name


def test_the_moments_the_reviewer_missed_are_framed_on_their_element() -> None:
    by_name = {shot.name: shot for shot in manifest.SHOTS}
    for name in ("events-webhook-question-channel", "improve-cleared-unattended-channel"):
        assert by_name[name].top == manifest.CHANNEL
        assert manifest.NEWEST_POST in by_name[name].must_see
    duplicates = by_name["events-duplicate-events-board"].seen("abc")
    assert duplicates == ('article.strip[data-run="abc"] .dups',)
    assert by_name["verify-graders-pass-still-wrong-sql"].bottom == manifest.SQL
    assert by_name["agent-confident-wrong-answer-gold"].bottom == manifest.GOLD


# --- the terminal renderer's cap on one long line -----------------------------------------------
def test_a_long_line_is_capped_with_a_marker() -> None:
    rows = term_render.prepare_rows("short\n" + "x" * 1000 + "\nend", max_line_rows=2)
    texts = [(r.kind, r.text) for r in rows]
    assert texts[1:3] == [("line", "x" * 100), ("cont", "x" * 100)]
    assert texts[3] == ("gap", "… 800 more characters of this line left out")
    assert texts[-1] == ("line", "end")
    assert len(term_render.prepare_rows("x" * 1000)) == 10  # no cap: every row, as before


def test_capped_wrapping_matches_the_kit_wrapping() -> None:
    line = " ".join(["word"] * 120)
    whole, left = term_render.wrap_capped(line, 100, None)
    capped, cut = term_render.wrap_capped(line, 100, 2)
    assert capped == whole[:2] and left == 0
    assert cut == len(line) - sum(len(p) + 1 for p in capped)


def test_the_log_keeps_every_edge_measure_the_frame_has() -> None:
    """Live, 25 October: the record named fields the frame no longer had, and every retake failed
    with an AttributeError after its scenario ran."""
    edges = framing.Edges(
        top=1, bottom=2, header=3, has_header=True, top_strokes=4, bottom_strokes=5
    )
    assert live_captures.edge_record(edges) == {
        "top": 1,
        "bottom": 2,
        "header": 3,
        "top_strokes": 4,
        "bottom_strokes": 5,
    }


# --- the retakes refused on 25 October 2026 ------------------------------------------------------
def _measure(top: float, bottom: float, **more: object) -> dict[str, object]:
    found: dict[str, object] = {
        "shown": True,
        "top": top,
        "bottom": bottom,
        "clipped": False,
        "inDialog": False,
        "viewportBottom": 720,
    }
    return {**found, **more}


def test_a_dialog_over_the_fixed_header_is_wholly_in_the_frame() -> None:
    """The Review dialog's top was at 54 CSS pixels, over the 60-pixel header it covers, and the
    dialog wholly in view was refused; an element of the page there is still under the header."""
    assert framing.in_view(_measure(54, 666, inDialog=True), 60) == framing.IN_VIEW
    assert framing.in_view(_measure(54, 666), 60) == framing.OUTSIDE
    assert framing.in_view(_measure(-2, 666, inDialog=True), 60) == framing.OUTSIDE
    assert framing.in_view(_measure(54, 730, inDialog=True), 60) == framing.OUTSIDE


def test_a_strip_past_its_lane_limit_is_hidden_not_out_of_view() -> None:
    """A run board lane shows its newest strips only (console.strips_per_lane), then N more: a
    strip past the limit has no box, and no scroll of the page or its lane can show it."""
    assert framing.in_view(_measure(0, 0, shown=False), 60) == framing.HIDDEN
    assert framing.in_view(None, 60) == framing.MISSING
    assert framing.in_view(_measure(300, 400, clipped=True), 60) == framing.OUTSIDE
    assert framing.in_view(_measure(300, 400), 60) == framing.IN_VIEW
    found = manifest.frame_problems(
        blockers=[],
        edges_clean=True,
        edges={},
        missing=[],
        image_check=[],
        hidden=['article.strip[data-run="abc"]'],
    )
    assert found == [
        "hidden on the page, so no frame can show it (a lane's strips past its limit are counted "
        'under N more): article.strip[data-run="abc"]'
    ]


class _Locator:
    def __init__(self, page: _Page, selector: str) -> None:
        self.page, self.selector = page, selector

    @property
    def first(self) -> _Locator:
        return self

    def count(self) -> int:
        return int(self.selector in self.page.measures)

    def evaluate(self, script: str) -> object:
        if script == framing.REVEAL:
            self.page.calls.append(f"reveal {self.selector}")
            return self.page.lane_moves
        return self.page.measures[self.selector]


class _Page:
    """Just enough of a Playwright page for where(), reveal(), and settle()."""

    def __init__(self, measures: dict[str, dict[str, object]], lane_moves: bool) -> None:
        self.measures = measures
        self.lane_moves = lane_moves
        self.calls: list[str] = []
        self.mouse = self
        buffer = io.BytesIO()
        Image.new("RGB", (400, 300), BACKGROUND).save(buffer, format="PNG")
        self.png = buffer.getvalue()

    def evaluate(self, script: str, argument: object = None) -> object:
        if script == framing.FIND_SCROLLER:
            return {"found": True, "top": 0, "room": 500, "headerBottom": 60, "modal": False}
        if script == framing.SCROLL_TO:
            self.calls.append(f"scroll {argument}")
            return argument
        return 2.0  # the device pixel ratio

    def locator(self, selector: str) -> _Locator:
        return _Locator(self, selector)

    def wait_for_timeout(self, milliseconds: int) -> None:
        self.calls.append(f"wait {milliseconds}")

    def move(self, x: int, y: int) -> None:
        pass

    def screenshot(self) -> bytes:
        self.calls.append("screenshot")
        return self.png


def test_where_names_each_must_see_selector_by_its_place() -> None:
    page = _Page(
        {"dialog": _measure(54, 666, inDialog=True), "strip": _measure(0, 0, shown=False)},
        lane_moves=False,
    )
    places = framing.where(page, ["dialog", "strip", "gone"])
    assert places == {"dialog": framing.IN_VIEW, "strip": framing.HIDDEN, "gone": framing.MISSING}
    assert framing.out_of_frame(page, ["dialog", "strip", "gone"]) == ["strip", "gone"]


def test_settle_reveals_the_lane_before_every_screenshot() -> None:
    """The board refits its lanes to the room left on the screen, so the lane is scrolled to the
    strip after each scroll of the page, not once before the frame is placed."""
    page = _Page({"strip": _measure(300, 400)}, lane_moves=True)
    _data, found, nudge = framing.settle(page, 100, nudges=(0,), lanes=["strip"])
    assert found.quiet and nudge == 0
    assert page.calls == ["scroll 100", "wait 150", "reveal strip", "wait 200", "screenshot"]
    still = _Page({"strip": _measure(300, 400)}, lane_moves=False)
    framing.settle(still, 100, nudges=(0,), lanes=["strip"])
    assert still.calls == ["scroll 100", "wait 150", "reveal strip", "screenshot"]


def test_the_retry_cap_images_start_at_the_row_of_buttons() -> None:
    by_name = {shot.name: shot for shot in manifest.SHOTS}
    for name in ("verify-retry-cap-escalated", "verify-retry-cap-no-cap-climbing"):
        shot = by_name[name]
        assert shot.top == manifest.VERIFY_BUTTONS
        assert manifest.LAST_VERIFY_BUTTON in shot.must_see  # the widest content in the frame
        assert {manifest.CHECKLIST, manifest.RUN_TOKENS} <= set(shot.must_see)
    assert manifest.STOPPED_AT_CAP in by_name["verify-retry-cap-escalated"].must_see


def _verify_frame(content_end: int) -> Image.Image:
    """A Verify page frame at 2560 by 1440: the page menu at the header's right (columns 2,484 to
    2,492), lines of text in the left column, and one line from column 180 to `content_end`."""
    image = Image.new("RGB", (2560, 1440), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rectangle((2484, 40, 2492, 90), fill=(20, 30, 40))
    for y in range(150, 1400, 60):
        draw.rectangle((180, y, 1100, y + 20), fill=(20, 30, 40))
    draw.rectangle((180, 1300, content_end, 1320), fill=(20, 30, 40))
    return image


def test_the_row_of_buttons_keeps_the_verify_frame_under_a_quarter_blank(tmp_path: Path) -> None:
    """The refused frames of 25 October ended their content at column 1,427 (1,058 columns blank
    up to the page menu); the row of buttons ends near column 1,920 (measured on the graders
    image), which leaves about 563, under the image check's quarter (640). The rule is unchanged."""
    check_images = _check_images()
    relative = "section-2-verification-loop/demo/expected/verify-retry-cap-escalated.png"
    refused, framed = tmp_path / "refused.png", tmp_path / "framed.png"
    _verify_frame(1425).save(refused)
    _verify_frame(1919).save(framed)
    assert [p.detail for p in check_images.check_image(refused, relative)] == [
        "1058 of 2560 columns are one colour"
    ]
    assert check_images.check_image(framed, relative) == []
