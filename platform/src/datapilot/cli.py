"""The `datapilot` command. Make targets are thin wrappers over these subcommands."""

from __future__ import annotations

import typer

from datapilot import db
from datapilot.contracts import registries
from datapilot.loop4_hill_climbing.data_cli import data_app

app = typer.Typer(no_args_is_help=True, add_completion=False)
app.add_typer(data_app)


@app.command()
def migrate() -> None:
    """Apply the ops schema migrations (owner role)."""
    db.wait_until_ready()
    applied = db.migrate()
    typer.echo(f"migrate: {len(applied)} applied" + (f" ({', '.join(applied)})" if applied else ""))


@app.command()
def spend() -> None:
    """The build's model spend by budget line and by activity, against pack.yaml's build_budget."""
    from datapilot.config import pack_config
    from datapilot.observability import spend as ledger

    budget = pack_config()["build_budget"]
    usage = ledger.line_usage()
    switch = budget.get("enabled_variable", "")
    if not ledger.build_budget_on():
        typer.echo(f"the build budget is off ({switch} is not 1): the lines below are not enforced")
    typer.echo("by budget line:")
    for line in ledger.budget_lines():
        if line.approval_variable:
            used = ledger.reserve_used()
            note = f"only with the owner's approval ({line.approval_variable}=1)"
        else:
            used, note = usage.get(line.name, (0, 0.0))[1], ""
        typer.echo(
            f"  {line.name:26} ${used:.4f} of ${line.cap_usd:.2f}, "
            f"${max(0.0, line.cap_usd - used):.4f} left  {note}".rstrip()
        )
    since, session = ledger.session_since(), ledger.session_limits()
    if since and session:
        this_session = ledger.line_usage(since=since)
        typer.echo(f"this session since {since} (the session limits, on top of the lines):")
        for name, cap in session.lines.items():
            used = this_session.get(name, (0, 0.0))[1]
            typer.echo(f"  {name:26} ${used:.4f} of ${cap:.2f} this session")
        spent = sum(dollars for _, dollars in this_session.values())
        typer.echo(f"  {'total':26} ${spent:.4f} of ${session.total_usd:.2f} this session")
    if "unassigned" in usage:
        typer.echo(f"  {'unassigned':26} ${usage['unassigned'][1]:.4f} (activities with no line)")
    typer.echo("by activity:")
    tokens = ledger.token_totals()
    for activity, calls, cost in ledger.by_activity():
        used_in, cached, used_out = tokens.get(activity, (0, 0, 0))
        share = f"{100 * cached / used_in:.0f} percent" if used_in else "none"
        typer.echo(
            f"  {activity:28} {calls:6} calls  ${cost:.4f}  {used_in:,} input tokens "
            f"({share} cached), {used_out:,} output tokens"
        )
    total = ledger.total_usd()
    typer.echo(
        f"total ${total:.4f} of ${budget['total_usd']:.2f} "
        f"(warning at ${budget['warn_usd']:.2f}, stop at ${budget['stop_usd']:.2f}); "
        f"ledger {ledger.ledger_path()}"
    )


@app.command()
def demos() -> None:
    """List every demo in platform/demos/registry.yaml with its command."""
    for demo in registries.demos().demos:
        typer.echo(f"{demo.id:36} {demo.tier.value:8} {demo.title}")


@app.command("check-registries")
def check_registries() -> None:
    """Validate both registries and their cross references."""
    problems = registries.cross_check(registries.demos(), registries.planted())
    for problem in problems:
        typer.echo(f"x {problem}")
    if problems:
        raise typer.Exit(1)
    typer.echo(
        f"registries: {len(registries.demos().demos)} demos, "
        f"{len(registries.planted().items)} planted items, 0 problems"
    )


@app.command()
def worker() -> None:
    """Run one worker process."""
    from datapilot.loop3_events.worker import main

    main()


@app.command()
def scheduler() -> None:
    """Run the scheduler process."""
    from datapilot.loop3_events.scheduler import main

    main()


@app.command()
def demo(
    name: str,
    planted_bugs: bool = typer.Option(
        False,
        "--planted",  # the option alone: an exported PLANTED never switches a half on
        help="The planted half: the demo's planted bugs on for its own runs only (PLANTED=1)",
    ),
) -> None:
    """Trigger a live demo through the api, as the console does: make demo NAME=<demo>, and
    make demo NAME=<demo> PLANTED=1 for its planted half (.env is never changed)."""
    from datapilot.loop3_events import commands

    _known(name, [d.id for d in registries.demos().demos], "demo")
    try:
        done = commands.demo(name, planted_bugs=planted_bugs, say=typer.echo)
    except commands.FinaleRefused as error:
        typer.echo(f"x {name} not sent: {error}")
        raise typer.Exit(1) from error
    except commands.DemoRefused as error:
        typer.echo(f"x {name}: {error}")
        raise typer.Exit(1) from error
    typer.echo(f"{name}: runs {done.run_ids or '-'}; requests {done.request_ids or '-'}")


@app.command()
def autonomy(
    level: str,
    by: str = typer.Option(..., "--by", help="Who sets it, for the status line and the record"),
) -> None:
    """Set the system's autonomy level through the api, as the console's control does:
    make autonomy LEVEL=unattended BY="<your name>". The finale needs the unattended level."""
    from datapilot.loop3_events import commands

    try:
        chosen = commands.set_autonomy(level, by=by)
    except ValueError as error:
        typer.echo(f"x {error}")
        raise typer.Exit(1) from error
    typer.echo(f"autonomy level: {chosen.label}, set by {by}")


@app.command()
def reset(name: str) -> None:
    """Clear one section's live state, release the kill switch: make reset NAME=<section>. The
    hill-climbing loop keeps this session's baseline experiment and says so."""
    _reset(name, discard_baseline=False)


@app.command("reset-discarding-baseline")
def reset_discarding_baseline(name: str) -> None:
    """The deliberate full reset of the hill-climbing loop: also discards this session's baseline
    experiment, so the next comparison needs a new baseline run."""
    _reset(name, discard_baseline=True)


def _known(name: str, valid: list[str], kind: str) -> None:
    """A misspelled name: one line naming the valid ones, never a traceback."""
    if name not in valid:
        typer.echo(f"x no {kind} named {name!r}; the {kind}s are {', '.join(valid)}")
        raise typer.Exit(1)


def _sections() -> list[str]:
    from datapilot.names import SECTIONS

    return [section.slug for section in SECTIONS]


def _reset(name: str, *, discard_baseline: bool) -> None:
    from datapilot.loop3_events import commands

    _known(name, _sections(), "section")
    try:
        report = commands.reset(name, discard_baseline=discard_baseline)
    except commands.ResetRefused as error:
        typer.echo(f"x {error}")
        raise typer.Exit(1) from error
    for line in report.lines():
        typer.echo(line)


archive_app = typer.Typer(
    name="archive",
    no_args_is_help=True,
    help="Read what the hill-climbing reset archived before it deleted or retired it.",
)
app.add_typer(archive_app)


@archive_app.command("list")
def archive_list(limit: int = typer.Option(20, help="How many resets, newest first")) -> None:
    """Every archived reset, newest first, with the experiments it archived."""
    from datapilot.loop3_events import archive

    with db.connect(db.Role.APP) as conn:
        found = archive.resets(conn, limit)
    if not found:
        typer.echo("the reset archive is empty")
    for entry in found:
        typer.echo(
            f"reset archive {entry.reset_id}: {entry.reset_by} at "
            f"{entry.reset_at.isoformat(timespec='seconds')}, live session "
            f"{entry.session_id or 'none'}, {entry.rows} rows"
        )
        for brief in entry.experiments:
            typer.echo(
                f"  experiment {brief['experiment_id']} of {brief['knowledge_version']}, started "
                f"{brief['started_at']}: dev {brief['dev'][0]} of {brief['dev'][1]}, holdout "
                f"{brief['holdout'][0]} of {brief['holdout'][1]}"
            )


@archive_app.command("show")
def archive_show(experiment_id: str) -> None:
    """One archived experiment: every item's result and confirmation, and its gate decisions."""
    from datapilot.loop3_events import archive

    with db.connect(db.Role.APP) as conn:
        found = archive.experiment(conn, experiment_id)
    if found is None:
        typer.echo(f"x no archived experiment {experiment_id}: `datapilot archive list` shows them")
        raise typer.Exit(1)
    for line in archive.experiment_lines(found):
        typer.echo(line)


safeguard_app = typer.Typer(
    name="safeguard",
    no_args_is_help=True,
    help="The class-day safeguard: the finale on the version verified in rehearsal, live.",
)
app.add_typer(safeguard_app)


@safeguard_app.command("verify")
def safeguard_verify(
    version: str,
    run: str = typer.Option(..., help="The run id of the version's correct finale in rehearsal"),
    by: str = typer.Option(..., help="Who verified it"),
) -> None:
    """In rehearsal: mark a knowledge version verified by its correct live finale run."""
    from datapilot.loop4_hill_climbing import versions

    with db.connect(db.Role.APP) as conn:
        try:
            found = versions.verify_in_rehearsal(conn, version, run, verified_by=by)
        except versions.SafeguardRefused as refused:
            typer.echo(f"x {refused}")
            raise typer.Exit(1) from refused
        conn.commit()
    typer.echo(f"verified in rehearsal: {found.describe()}")


@safeguard_app.command("activate")
def safeguard_activate(
    by: str = typer.Option(..., help="Who activates it (the instructor)"),
    version: str | None = typer.Option(
        None,
        help="A verified version, taken whatever its age (make ... NAME=<version>); unnamed, the "
        "newest, only when it is recent and from this stack's rehearsal",
    ),
) -> None:
    """In class, when the live candidate's finale answer is wrong: make the version verified in
    rehearsal the active one, recorded as a safeguard activation, then run the finale live again."""
    from datapilot.loop4_hill_climbing import versions

    with db.connect(db.Role.APP) as conn:
        try:
            done = versions.activate_verified(conn, activated_by=by, name=version or None)
        except versions.SafeguardRefused as refused:
            typer.echo(f"x {refused}")
            raise typer.Exit(1) from refused
        conn.commit()
    typer.echo(f"{done.version}: {done.verification.provenance()}")
    for caution in done.cautions:
        typer.echo(f"  taken because it was named, although {caution}")
    typer.echo(f"{done.sentence} (promotion decision {done.decision_id})")
    typer.echo(
        "now run the finale live on it: make demo NAME=improve-cleared-unattended, or Events > "
        "Send webhook question in the console"
    )


@safeguard_app.command("status")
def safeguard_status() -> None:
    """The newest version verified in rehearsal, its age and session, whether make
    safeguard-activate would take it, and whether it is active."""
    from datapilot.loop4_hill_climbing import versions

    with db.connect(db.Role.APP) as conn:
        found = versions.latest_verification(conn)
        active = versions.active_name(conn)
    if found is None:
        typer.echo("no knowledge version is verified in rehearsal yet")
        return
    typer.echo(f"verified in rehearsal: {found.describe()}")
    typer.echo(f"  {found.provenance()}")
    problems = found.problems(versions.age_limit_days())
    if problems:
        typer.echo(f"x  make safeguard-activate refuses it: {'; and '.join(problems)}")
        typer.echo(f"   to {versions.VERIFY_AGAIN}")
    else:
        typer.echo("ok make safeguard-activate takes it")
    typer.echo(
        f"active knowledge version: {active}"
        + (" (the safeguard's)" if active == found.version else "")
    )


@app.command("open-code")
def open_code(name: str) -> None:
    """Open the code a section shows in class: make open-code NAME=<section>."""
    from datapilot.loop3_events import commands

    _known(name, _sections(), "section")
    for ref in commands.open_code(name) or ["(no code ranges in the demo registry yet)"]:
        typer.echo(ref)


if __name__ == "__main__":
    app()
