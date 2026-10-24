"""The data and hill-climbing commands: `datapilot seed`, `check-data`, `preflight`,
`hill-climbing-runner`, and `calibrate <step>` (make seed, make check-data, make preflight,
make hill-climbing-runner, make calibrate STEP=<step>)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import typer

from datapilot.loop4_hill_climbing.pack_files import load_submodule

data_app = typer.Typer(no_args_is_help=True, add_completion=False)


def _seed_module():
    return load_submodule("data_generator", "seed")


@data_app.command()
def seed() -> None:
    """Generate and load warehouse and warehouse_alt, then apply the agent role's settings."""
    seeding = _seed_module()
    started = time.monotonic()
    for warehouse in seeding.DATABASES:
        report = seeding.seed(warehouse)
        counts = ", ".join(f"{table} {n:,}" for table, n in report.counts.items())
        typer.echo(f"seed {warehouse}: {counts} in {report.seconds:.1f} s")
        typer.echo(f"seed {warehouse}: content hash {report.content_hash}")
    typer.echo(f"seed: done in {time.monotonic() - started:.1f} s")


@data_app.command("check-data")
def check_data() -> None:
    """Compare row counts and the content hash of both warehouses with expected.yaml."""
    seeding = _seed_module()
    problems = [p for warehouse in seeding.DATABASES for p in seeding.check(warehouse)]
    for problem in problems:
        typer.echo(f"x {problem}")
    if problems:
        raise typer.Exit(1)
    typer.echo("check-data: both warehouses match expected.yaml")


# --- live wiring ---------------------------------------------------------------------------------
def _tracing(project: str | None = None) -> tuple[Any, Any]:
    """(tracer, links) for runs traced to the given project (the experiments one by default); (None,
    None) without a key."""
    from datapilot.observability.traces import FeedbackTracer, export_tracing_env, live_links
    from datapilot.settings import get_settings

    settings = get_settings()
    project = project or settings.langsmith_experiments_project
    export_tracing_env(settings, project)
    found = live_links(settings, project)
    if found is None:
        return None, None
    client, links = found
    return FeedbackTracer(client, links), links


def _analyst(feature: str) -> Any:
    """The analyst for a live development run: traced to datapilot-development with its track and
    feature tags."""
    from datapilot.loop4_hill_climbing.targets import analyst
    from datapilot.observability.traces import development_project, development_tags

    return analyst(project=development_project(), tags=development_tags(feature, "calibration"))


def _context(echo: Callable[[str], None] = typer.echo) -> Any:
    from datapilot import db
    from datapilot.config import pack_config
    from datapilot.loop4_hill_climbing import store
    from datapilot.loop4_hill_climbing.calibration import Context
    from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator
    from datapilot.loop4_hill_climbing.pack_files import load_benchmark
    from datapilot.observability.traces import development_project

    tracer, _ = _tracing(development_project())
    with db.connect(db.Role.APP) as conn:
        session_id = store.open_session(conn)
    return Context(
        session_id=session_id,
        items=load_benchmark(),
        evaluator=ExecutionEvaluator.live(),
        tracer=tracer,
        concurrency=pack_config()["evaluation"]["concurrency"],
        echo=echo,
    )


@data_app.command()
def preflight(
    purpose: str = typer.Option(..., help="class, rehearsal, thursday-review, or development."),
) -> None:
    """Check the services, the OpenAI key, and the drift canary; then start the live session."""
    from datapilot import db
    from datapilot.contracts.live import SessionPurpose
    from datapilot.loop3_events import sessions
    from datapilot.loop4_hill_climbing import preflight as checks
    from datapilot.loop4_hill_climbing import versions
    from datapilot.loop4_hill_climbing.calibration import use_activity
    from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator
    from datapilot.loop4_hill_climbing.pack_files import load_benchmark
    from datapilot.loop4_hill_climbing.targets import analyst
    from datapilot.observability.traces import development_project, flush
    from datapilot.settings import get_settings

    try:
        chosen = SessionPurpose(purpose)
    except ValueError as error:
        raise typer.BadParameter(f"use one of {[p.value for p in SessionPurpose]}") from error
    # preflight-development counts under development live checks; the others under rehearsal
    use_activity(f"preflight-{chosen.value}", prefix="")
    settings = get_settings()

    def install() -> list[str]:
        with db.connect(db.Role.APP) as conn:
            added = versions.install(conn)
            conn.commit()
        return added

    def canary() -> list[checks.CanaryRun]:
        # a development session is a live development run; the others trace with the experiments
        development = chosen is SessionPurpose.DEVELOPMENT
        tracer, _ = _tracing(development_project() if development else None)
        target = _analyst("preflight") if development else analyst()
        return checks.run_canary(
            target, ExecutionEvaluator.live(), load_benchmark(), checks.canary_ids(), tracer
        )

    report = checks.preflight(
        chosen,
        settings,
        canary=canary,
        start_session=sessions.start_session,
        services=lambda: checks.service_checks(settings),
        key=lambda: checks.key_check(settings),
        install=install,
    )
    flush()
    for check in report.checks:
        typer.echo(check.line())
    for run in report.canary:
        word = "as expected" if run.as_expected else "NOT as expected"
        outcome = "passed" if run.passed else "failed"
        typer.echo(f"canary {run.kind:4} {run.item_id:40} {outcome}, {word}  {run.trace_url or ''}")
        typer.echo(f"       {run.reason}")
    if report.stopped:
        typer.echo(report.stopped)
        raise typer.Exit(1)
    assert report.session is not None
    started = report.session.started_at
    typer.echo(
        f"Live session started at {started.astimezone():%H:%M:%S} local time "
        f"({started.isoformat(timespec='seconds')} UTC), purpose {chosen.value}, "
        f"session {report.session.session_id}; model id {report.model_id}"
    )


@data_app.command("hill-climbing-runner")
def hill_climbing_runner() -> None:
    """Serve the Improve page: experiments, the analyzer team, promotions, and gold checks. The
    Compose service of this name runs it; a second runner on the same database refuses to start."""
    import threading
    from dataclasses import replace

    from datapilot import db
    from datapilot.config import pack_config
    from datapilot.loop3_events import improvement
    from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator
    from datapilot.loop4_hill_climbing.measurement import Scheme
    from datapilot.loop4_hill_climbing.pack_files import load_benchmark
    from datapilot.loop4_hill_climbing.runner import (
        ALREADY_SERVING,
        HillClimbingRunner,
        RunnerAlreadyServing,
        kill_switch_stop,
    )
    from datapilot.loop4_hill_climbing.targets import analyst

    with db.connect(db.Role.APP, autocommit=True) as conn:
        serving = improvement.runner_serving(conn)
    if serving:
        typer.echo(f"x {ALREADY_SERVING}")
        raise typer.Exit(2)
    tracer, links = _tracing()
    runner = HillClimbingRunner(
        items=load_benchmark(),
        target=replace(analyst(), external_stop=kill_switch_stop),
        evaluator=ExecutionEvaluator.live(),
        scheme=Scheme.from_pack(),
        concurrency=pack_config()["evaluation"]["concurrency"],
        tracer=tracer,
        project_url=links.project_url() if links else None,
    )
    typer.echo("hill-climbing runner ready")
    try:
        runner.serve(threading.Event())
    except RunnerAlreadyServing as error:  # another one started in the moment since the check
        typer.echo(f"x {error}")
        raise typer.Exit(2) from error


@data_app.command("live-smoke")
def live_smoke() -> None:
    """Five real calls across the system, each with its result, tokens, cost, and trace link.
    Fails only on hard breakages; spend goes under "development live checks"."""
    from datapilot.loop4_hill_climbing import live_smoke as smoke
    from datapilot.loop4_hill_climbing.calibration import (
        OverWarningLine,
        guard_budget,
        use_activity,
    )
    from datapilot.settings import get_settings

    use_activity(smoke.ACTIVITY, prefix="")
    model = get_settings().agent_model
    estimate = smoke.estimate_usd(model)
    try:
        typer.echo(guard_budget(f"live smoke on {model}", estimate, smoke.ACTIVITY))
    except OverWarningLine as stop:
        typer.echo(str(stop))
        raise typer.Exit(2) from stop
    checks = smoke.run(smoke.live_services())
    for check in checks:
        for line in check.lines():
            typer.echo(line)
    actual = sum(c.cost_usd for c in checks)
    typer.echo("per run (for the cost per run):")
    for check in checks:
        typer.echo(
            f"  {check.name[:3]} {check.tokens_in + check.tokens_out:>9,} tokens "
            f"({check.tokens_in:,} in, {check.tokens_out:,} out)  ${check.cost_usd:.4f}"
        )
    failures = [c for c in checks if not c.ok]
    typer.echo(
        f"live smoke: {len(checks) - len(failures)} of {len(checks)} without a hard breakage; "
        f"actual ${actual:.4f} against the estimate ${estimate:.4f}"
    )
    if failures:
        raise typer.Exit(1)


def output_token_cap() -> None:
    """The live probe of the per-call output-token cap (make calibrate STEP=output-token-cap): one
    analyst run with the analyst's cap lowered for this run only must end escalated at the cap.
    Spend goes under "development live checks"."""
    from datapilot.loop4_hill_climbing import live_smoke as smoke
    from datapilot.loop4_hill_climbing.calibration import (
        OverWarningLine,
        estimate,
        guard_budget,
        use_activity,
    )
    from datapilot.settings import get_settings

    use_activity(smoke.ACTIVITY, prefix="")
    model = get_settings().agent_model
    projected = estimate(1, model, "analyst")
    try:
        typer.echo(guard_budget(f"output-token cap probe on {model}", projected, smoke.ACTIVITY))
    except OverWarningLine as stop:
        typer.echo(str(stop))
        raise typer.Exit(2) from stop
    services = smoke.live_services()
    check = smoke.output_cap_probe(services)
    smoke.confirm_traces(services, [check])
    for line in [*check.lines(), f"    run {check.run_id}"]:
        typer.echo(line)
    if not check.ok:
        raise typer.Exit(1)


# --- calibration ---------------------------------------------------------------------------------
DEVELOPMENT_TARGET = "datapilot.loop4_hill_climbing.targets:development_analyst"
calibrate_app = typer.Typer(no_args_is_help=True, add_completion=False)
data_app.add_typer(calibrate_app, name="calibrate", help="Calibration steps (live model calls).")


def _load_target(spec: str):
    """A 'module:function' factory that returns the target (question, version) -> answer."""
    import importlib

    module, _, name = spec.partition(":")
    if not name:
        raise typer.BadParameter("use module:function, such as mypackage.targets:analyst")
    return getattr(importlib.import_module(module), name)()


def _step(
    step: str,
    *,
    runs: int,
    model: str,
    kind: str,
    body: Callable[[Any], dict[str, Any]],
    summary: Callable[[dict[str, Any]], str],
    estimate_usd: float | None = None,
) -> None:
    """Estimate, check the warning line, run live, and write the raw results and the run log."""
    from datapilot.loop4_hill_climbing import calibration as cal
    from datapilot.observability.traces import flush

    activity = cal.use_activity(step)
    estimate = cal.estimate(runs, model, kind) if estimate_usd is None else estimate_usd
    try:
        typer.echo(cal.guard_budget(step, estimate))
    except cal.OverWarningLine as stop:
        typer.echo(str(stop))
        raise typer.Exit(2) from stop
    ctx = _context()
    before, started = cal.activity_spent(activity), cal.now()
    data = body(ctx)
    flush()
    cost = cal.activity_spent(activity) - before
    record = cal.StepRecord(
        step=step,
        activity=activity,
        session_id=str(ctx.session_id),
        started_at=started,
        finished_at=cal.now(),
        estimate_usd=round(estimate, 6),
        cost_usd=round(cost, 6),
        summary=summary(data),
        data=data,
    )
    path = cal.write(record)
    typer.echo(f"{step}: {record.summary}; cost ${cost:.4f} (estimate ${estimate:.4f}); {path}")


def _model() -> str:
    """The class model (OPENAI_MODEL): calibration measures only the model the class uses."""
    from datapilot.settings import get_settings

    return get_settings().agent_model


def _with_runs(target: Any, data: dict[str, Any]) -> dict[str, Any]:
    from datapilot.loop4_hill_climbing.calibration import run_rows

    return {**data, "model_ids": target.model_ids.as_rows(), "run_stats": run_rows(target)}


@calibrate_app.command("canary")
def calibrate_canary() -> None:
    """The drift canary on its own: three easy questions pass, two trap questions fail."""
    from datapilot.loop4_hill_climbing import preflight as checks

    ids = checks.canary_ids()

    def body(ctx: Any) -> dict[str, Any]:
        target = _analyst("calibration-canary")
        runs = checks.run_canary(target, ctx.evaluator, ctx.items, ids, ctx.tracer)
        return _with_runs(target, {"runs": [vars(r) for r in runs]})

    _step(
        "canary",
        runs=len(ids["easy"]) + len(ids["traps"]),
        model=_model(),
        kind="analyst",
        body=body,
        summary=lambda d: (
            f"{sum(r['passed'] for r in d['runs'] if r['kind'] == 'easy')} easy "
            f"passed, {sum(not r['passed'] for r in d['runs'] if r['kind'] == 'trap')} traps failed"
        ),
    )


@calibrate_app.command("traps")
def calibrate_traps(
    runs: int = typer.Option(3, help="Runs per trap item."),
) -> None:
    """Every trap item several times under the starting knowledge; each must fail every time."""
    from datapilot.loop4_hill_climbing.calibration import trap_items, traps_step
    from datapilot.loop4_hill_climbing.pack_files import load_benchmark

    def body(ctx: Any) -> dict[str, Any]:
        target = _analyst("calibration-traps")
        return _with_runs(target, traps_step(ctx, target, runs))

    _step(
        "traps",
        runs=runs * len(trap_items(load_benchmark())),
        model=_model(),
        kind="analyst",
        body=body,
        summary=lambda d: (
            f"{len(d['passed_at_least_once'])} trap items passed at least once of {len(d['items'])}"
        ),
    )


@calibrate_app.command("experiment")
def calibrate_experiment(
    version: str = typer.Option(..., help="The knowledge version to measure."),
) -> None:
    """The gate's measurement scheme on the 40 items under one version."""
    from datapilot.loop4_hill_climbing.calibration import experiment_step
    from datapilot.loop4_hill_climbing.measurement import Scheme
    from datapilot.loop4_hill_climbing.pack_files import load_benchmark

    scheme, items = Scheme.from_pack(), load_benchmark()
    runs = sum(scheme.repeats(i.split) for i in items)

    def body(ctx: Any) -> dict[str, Any]:
        target = _analyst("calibration-experiment")
        return _with_runs(target, experiment_step(ctx, target, version))

    _step(
        "experiment",
        runs=runs,
        model=_model(),
        kind="analyst",
        body=body,
        summary=lambda d: (
            f"{d['knowledge_version']} on {d['model']}: holdout {d['holdout_passes']} "
            f"of {d['holdout_total']}, dev {d['dev_passes']} of {d['dev_total']}, "
            f"{d['wall_seconds']} s"
        ),
    )


@calibrate_app.command("analyzer")
def calibrate_analyzer() -> None:
    """The analyzer team (OPENAI_ANALYZER_MODEL), from the failed dev items of the starting
    version."""
    from datapilot.loop4_hill_climbing.calibration import analyzer_step
    from datapilot.settings import get_settings

    model = get_settings().analyzer_model

    _step(
        "analyzer",
        runs=1,
        model=model,
        kind="analyzer",
        body=lambda ctx: analyzer_step(ctx, _model()),
        summary=lambda d: (
            f"{d['candidate_version']} on {d['model']}: {len(d['proposed'])} proposed, "
            f"{len(d['kept_by_critic'])} kept by the critic, {len(d['accepted'])} passed the guard"
        ),
    )


@calibrate_app.command("analyzer-high")
def calibrate_analyzer_high(
    effort: str = typer.Option("high", help="The analyzer team's reasoning effort to measure."),
) -> None:
    """The analyzer team at reasoning effort high, from the same failed dev items as the analyzer
    step (this session's experiment of v1), then the candidate experiment against that experiment,
    recording its holdout passes. The cost estimate is printed before any model call."""
    from datapilot import db
    from datapilot.loop4_hill_climbing import calibration as cal
    from datapilot.loop4_hill_climbing import store, versions
    from datapilot.loop4_hill_climbing.measurement import Scheme
    from datapilot.loop4_hill_climbing.pack_files import load_benchmark
    from datapilot.settings import get_settings

    items, analyzer_model = load_benchmark(), get_settings().analyzer_model
    with db.connect(db.Role.APP) as conn:
        session_id = store.open_session(conn)
    if cal.latest_experiment(session_id, versions.STARTING_VERSION, _model()) is None:
        typer.echo(
            f"analyzer-high: no experiment of {versions.STARTING_VERSION} in this live session; "
            "run make calibrate STEP=experiment-starting first. Nothing was called."
        )
        raise typer.Exit(2)

    def body(ctx: Any) -> dict[str, Any]:
        target = _analyst("calibration-analyzer-high")
        return _with_runs(target, cal.analyzer_effort_step(ctx, target, effort))

    _step(
        "analyzer-high",
        runs=0,
        model=analyzer_model,
        kind="analyzer",
        body=body,
        summary=lambda d: (
            f"{d['candidate_version']} at effort {d['reasoning_effort']}: holdout "
            f"{d['holdout_passes']} (starting version, candidate), regressions {d['regressions']}"
        ),
        estimate_usd=cal.analyzer_effort_estimate(
            items, Scheme.from_pack(), _model(), analyzer_model
        ),
    )


@calibrate_app.command("stability")
def calibrate_stability(
    version: str = typer.Option(..., help="The knowledge version to run under."),
    target: str = typer.Option(
        DEVELOPMENT_TARGET,
        help="module:function returning the analyst target.",
    ),
    runs: int | None = typer.Option(None, help="Runs per holdout item (pack.yaml by default)."),
) -> None:
    """Run each holdout item several times under one version; list the unstable items."""
    from dataclasses import replace

    from datapilot.contracts import Split
    from datapilot.loop4_hill_climbing.calibration import stability_step
    from datapilot.loop4_hill_climbing.pack_files import load_benchmark
    from datapilot.loop4_hill_climbing.stability import Limits

    limits = Limits.from_pack()
    if runs is not None:
        limits = replace(limits, runs=runs)
    holdout = sum(1 for i in load_benchmark() if i.split is Split.HOLDOUT)

    def body(ctx: Any) -> dict[str, Any]:
        chosen = _load_target(target)
        return _with_runs(chosen, stability_step(ctx, chosen, version, limits))

    _step(
        "stability",
        runs=holdout * limits.runs,
        model=_model(),
        kind="analyst",
        body=body,
        summary=lambda d: d["lines"][-1],
    )


@calibrate_app.command("agents")
def calibrate_agents(
    items: str = typer.Option(
        "net-revenue-fiscal-2025,product-count,top-customers-fiscal-2025,camping-subcategories",
        help="Comma-separated benchmark item ids.",
    ),
) -> None:
    """Tokens and latency per question with the schema scout and the reviewer on and off."""
    from datapilot.loop4_hill_climbing.calibration import AGENT_CONFIGS, AMBIGUOUS, agents_step

    chosen = [i.strip() for i in items.split(",") if i.strip()]

    def body(ctx: Any) -> dict[str, Any]:
        return agents_step(ctx, _analyst("calibration-agents"), chosen)

    _step(
        "agents",
        runs=(len(chosen) + len(AMBIGUOUS)) * len(AGENT_CONFIGS),
        model=_model(),
        kind="analyst",
        body=body,
        summary=lambda d: "; ".join(
            f"{label}: {c['mean_tokens']} tokens, {c['mean_seconds']} s"
            for label, c in d["configs"].items()
        ),
    )


@calibrate_app.command("confirm")
def calibrate_confirm(
    item: str | None = typer.Option(None, help="A holdout item id (chosen from the results)."),
    version: str | None = typer.Option(None, help="The version it runs under (chosen too)."),
) -> None:
    """The confirming re-run of an apparent holdout regression, through the gate's code. Without
    options it takes a real apparent regression from the newest candidate experiment, else the
    least stable holdout item from the newest stability results."""
    from datapilot.loop4_hill_climbing.calibration import confirm_choice, confirm_step

    if item is None or version is None:
        from datapilot.loop4_hill_climbing.pack_files import load_benchmark

        item, version = confirm_choice(known={i.id for i in load_benchmark()})
        typer.echo(f"confirm: {item} under {version}")
    from datapilot.loop4_hill_climbing.measurement import Scheme

    scheme = Scheme.from_pack()

    def body(ctx: Any) -> dict[str, Any]:
        target = _analyst("calibration-confirm")
        return _with_runs(target, confirm_step(ctx, target, item, version))

    _step(
        "confirm",
        runs=scheme.holdout_repeats + scheme.holdout_regression_reruns,
        model=_model(),
        kind="analyst",
        body=body,
        summary=lambda d: (
            f"{d['item_id']} under {d['knowledge_version']}: first runs "
            f"{d['first_runs']}, confirmed {d['confirmed']}, cleared {d['cleared']}"
        ),
    )


# Steps named by one word, for make calibrate STEP=<word> (the WSL wrapper passes no options).
@calibrate_app.command("experiment-starting")
def calibrate_experiment_starting() -> None:
    """The measurement scheme under the starting knowledge (v1)."""
    calibrate_experiment(version="v1")


@calibrate_app.command("experiment-candidate")
def calibrate_experiment_candidate() -> None:
    """The measurement scheme under the newest candidate, compared with v1 (holdout flips and
    confirmed regressions)."""
    calibrate_experiment(version=_candidate())


@calibrate_app.command("stability-starting")
def calibrate_stability_starting() -> None:
    """The stability filter under the starting knowledge."""
    calibrate_stability(version="v1", target=DEVELOPMENT_TARGET, runs=None)


@calibrate_app.command("stability-candidate")
def calibrate_stability_candidate() -> None:
    """The stability filter under the newest candidate (the version the gate would promote)."""
    calibrate_stability(version=_candidate(), target=DEVELOPMENT_TARGET, runs=None)


@calibrate_app.command("experiment-active")
def calibrate_experiment_active() -> None:
    """The measurement scheme under the active (promoted) version, compared with v1."""
    calibrate_experiment(version=_active())


@calibrate_app.command("stability-active")
def calibrate_stability_active() -> None:
    """The stability filter under the active (promoted) version."""
    calibrate_stability(version=_active(), target=DEVELOPMENT_TARGET, runs=None)


# A development live check, not a calibration measurement: it is a calibrate step only because
# make calibrate STEP=<word> is the way the WSL wrapper starts one live command by name.
calibrate_app.command("output-token-cap")(output_token_cap)


def _active() -> str:
    from datapilot import db
    from datapilot.loop4_hill_climbing import versions

    with db.connect(db.Role.APP) as conn:
        return versions.active_name(conn)


def _candidate() -> str:
    from datapilot import db
    from datapilot.loop4_hill_climbing import versions

    with db.connect(db.Role.APP) as conn:
        found = versions.latest_candidate(conn)
    if found is None:
        typer.echo("no candidate version yet: run make calibrate STEP=analyzer first")
        raise typer.Exit(2)
    return found
