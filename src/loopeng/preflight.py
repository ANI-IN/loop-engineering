"""Two cents' worth of checks, before anything expensive.

The smallest live path used to be `--profile delivery`: 4 cells, 50 items, ~200 calls,
projected est. $0.43. A first-time cloner had no way to spend a fraction of a cent
finding out whether their key was valid, whether both model ids resolved **on their
account**, and whether the warehouse and gold set built at all. They found out by
starting the thing that spends.

So this runs in order, prints pass/fail per line, and stops at the first failure that
makes the next check meaningless. Four properties are load-bearing:

**Each model is called with the request kwargs the registry declares.** Not a
simplified probe call. `temperature=0` is legal on the judge and a 400 on both
scoring roles, and a
preflight that omitted the kwargs would pass on an account where the sweep fails.

**Only `max_tokens` is trimmed, and only if it can be.** It caps thinking plus output on
the frontier role, so it is left alone there; cost is driven by the tokens actually
produced, and "reply with one word" produces few of them either way.

**Steps 3 and 4 make no network calls at all.** The warehouse, the gold set and the rule
surface are offline, so they are checked even when the key is bad — a cloner with a typo
still learns that the rest of their checkout is sound.

**Cost carries `est.`** Tokens are measured; dollars are a price table. §13 is right.
"""

from dataclasses import dataclass, field
from pathlib import Path

import structlog

from loopeng.gold.build import build_gold, clustering_summary
from loopeng.providers import build_client, complete, triage_call_failure
from loopeng.registry import (
    REGISTRY,
    SCORING_ROLES,
    key_variable_for_role,
    spec_for,
)
from loopeng.settings import (
    KEY_FIELDS,
    REQUIRED_CREDENTIALS,
    MissingCredential,
    Settings,
    load_settings,
)
from loopeng.usage import CallUsage, UsageLedger
from loopeng.verify.probes import run_probes
from loopeng.warehouse.connect import StaleWarehouse, ensure_warehouse

log = structlog.get_logger(__name__)

# Every credential a live path needs, in the order they are reported.
KEY_VARS = tuple(dict.fromkeys(key_variable_for_role(role) for role in sorted(REGISTRY)))

PROBE_PROMPT = "Reply with the single word: ok"

# A system block, because that is where every real call puts its static prefix. A
# probe that omitted it would exercise a request shape the sweep never sends.
PROBE_SYSTEM = "You are a preflight check. Answer in one word."

NEXT_COMMAND = (
    "uv run python demos/04_hill_climbing_loop/sweep.py --profile smoke --foreground"
)


@dataclass
class Step:
    """One check, its verdict, and what to do about it.

    `detail` is what the operator reads; `fix` is present only on a failure, because a
    remedy printed beside a pass is noise that trains people to skip the line.
    """

    name: str
    ok: bool
    detail: str
    fix: str | None = None
    # A check that was NOT ATTEMPTED, and correctly so. Distinct from a pass, because
    # "we did not look" and "we looked and it was fine" are different facts and this
    # whole module exists to keep those apart. `ok` stays True so an optional probe
    # cannot fail the preflight; `skipped` is what stops it claiming a result.
    skipped: bool = False

    def render(self) -> str:
        if self.skipped:
            return f"[SKIP] {self.name} — {self.detail}"
        mark = "PASS" if self.ok else "FAIL"
        line = f"[{mark}] {self.name} — {self.detail}"
        if self.ok:
            return line
        # Continuation lines are indented to the same gutter. The triage messages are
        # multi-line by design — they name the variable, the fix and the API's own words
        # — and unindented they run back into the left margin and stop reading as one
        # block belonging to one failed check.
        body = "\n".join(
            f"       {'fix: ' if index == 0 else '     '}{part}"
            for index, part in enumerate((self.fix or "").splitlines())
        )
        return f"{line}\n{body}"


@dataclass
class Preflight:
    steps: list[Step] = field(default_factory=list)
    ledger: UsageLedger = field(default_factory=UsageLedger)

    @property
    def ok(self) -> bool:
        return all(step.ok for step in self.steps)

    def add(self, step: Step) -> Step:
        self.steps.append(step)
        return step

    def cost_line(self) -> str:
        """Always `est.`. Tokens are measured, dollars are a hand-entered table."""
        totals = self.ledger.totals()
        return (
            f"est. ${self.ledger.cost_usd():.6f} over {totals['n_calls']} call(s) "
            f"({totals['input_tokens']} in, {totals['output_tokens']} out)"
        )


def _skip_optional_role(role: str, settings: Settings) -> Step | None:
    """A `Step` when this role must not be probed, or None to probe it.

    The preflight looped over every role in the registry and built a client for each,
    including the JUDGE — whose key README §10 and SECURITY.md both call optional
    because the judge never gates a result. So a checkout following the documented
    minimal setup crashed in the one command written to tell it what is wrong.

    That is the required-credential defect from two commits ago, still live one layer
    down: making the key optional in `settings` did not make it optional in the tool
    that checks your setup.

    A skip rather than a pass. "We did not call it" and "we called it and it worked"
    are different facts, and reporting the first as the second is how a preflight tells
    someone their triage path is fine when it has never been exercised.
    """
    field = KEY_FIELDS[spec_for(role).provider]
    if role in SCORING_ROLES or getattr(settings, field) is not None:
        return None
    return Step(
        f"{role} model reachable ({spec_for(role).model_id})", True,
        f"not called — {field.upper()} is not set, and this role gates nothing. "
        f"Every scored figure in a session is produced without it; only triage and "
        f"failure sorting need it.",
        skipped=True,
    )


def _required_vars() -> str:
    """The credentials a live run actually needs, named. One, today."""
    return " and ".join(field.upper() for field in REQUIRED_CREDENTIALS)


def _is_are() -> str:
    """Agrees with however many credentials are required.

    The step name was a fixed "X and Y are set". Deriving the list made it read
    "OPENAI_API_KEY are set" the moment the required set became one — the sort of thing
    that survives a green suite and is read out loud at a venue.
    """
    return "are" if len(REQUIRED_CREDENTIALS) > 1 else "is"


def check_key(settings=None) -> Step:
    """Are the REQUIRED credentials present?

    Required is one key, not two, and the step says so rather than listing both vendors.
    The Anthropic key buys the judge, the judge never gates, and a preflight that fails
    without it would turn away a checkout that can run every scored path in the session.
    That contradiction shipped: `REQUIRED_CREDENTIALS` demanded both while README §10
    said one, so this step refused a valid setup and blamed a key nothing needed.

    `load_settings` reports EVERY missing required credential rather than the first, so
    an operator half an hour from a session fixes them in one pass instead of fixing
    one, re-running, and finding the next.
    """
    # Derived from REQUIRED_CREDENTIALS, not from the list of vendors this project
    # calls. Those are different sets now, and the step name is what an operator reads
    # when it fails.
    listed = _required_vars()
    try:
        settings = settings or load_settings()
    except MissingCredential as exc:
        return Step(
            f"{listed} {_is_are()} set", False, "; ".join(str(exc).splitlines()),
            fix=f"cp .env.example .env, then fill in {listed}. "
                f"ANTHROPIC_API_KEY (the judge) and LANGSMITH_API_KEY are optional and "
                f"can stay empty — neither gates a measurement.",
        )
    return Step(f"{listed} {_is_are()} set", True, "present (values never printed or logged)")


def check_model(role: str, *, client=None, ledger: UsageLedger) -> Step:
    """One minimal call, with the registry's own kwargs. Records what it billed.

    **The client is built INSIDE the try**, and that is not tidiness. It was built
    above it, so a missing credential escaped as an unhandled `MissingCredential` and
    the preflight — the one command whose entire job is to fail readably before you
    spend anything — printed a twelve-line traceback instead of the sentence that names
    the variable and the fix.
    """
    spec = spec_for(role)

    try:
        client = build_client(spec) if client is None else client
        completion = complete(
            spec,
            system=PROBE_SYSTEM,
            messages=[{"role": "user", "content": PROBE_PROMPT}],
            client=client,
        )
    except Exception as exc:  # noqa: BLE001 - the verdict IS the exception
        _termination, message = triage_call_failure(exc, spec=spec)
        ledger.record(CallUsage(spec.model_id, "error"))
        return Step(
            f"{role} model reachable ({spec.model_id})", False,
            f"the call was refused: {type(exc).__name__}", fix=message,
        )

    usage = ledger.record(completion.usage)
    return Step(
        f"{role} model reachable ({spec.model_id})", True,
        f"answered with the registry's own kwargs as {completion.served_model} "
        f"({usage.input_tokens} in, {usage.output_tokens} out)",
    )


def check_warehouse_and_gold(*, warehouse_path: Path, seed: int) -> tuple[Step, Step]:
    """Offline. Runs even when the key is bad, so a typo does not hide the rest.

    **It checks the warehouse's VOCABULARY, not just that a file is there, and the
    difference is the one this preflight exists for.**

    Every figure this project renders is computed during the session. That guarantee
    protects against a stale NUMBER. It does nothing against a stale SUBSTRATE — a
    warehouse generated before the schema's categories and regions were widened
    produces perfectly fresh figures computed from the wrong world, and every one of
    them carries a live timestamp.

    Measured, not hypothetical: a 120-call run scored exactly zero on every arm,
    including the pattern that requires no rules, because the local warehouse
    predated the widening. That failure was caught only because zero everywhere is
    loud. A PARTIAL overlap — some slices present, some missing — would have produced
    a plausible number on a chart and nobody would have looked twice.

    `ensure_warehouse` raises `StaleWarehouse` for exactly this, and the preflight is
    where an operator should meet it: thirty minutes before the session, with the fix
    named, rather than at minute forty of a stage.
    """
    try:
        warehouse = ensure_warehouse(warehouse_path, seed=seed)
    except StaleWarehouse as exc:
        return (
            Step("warehouse matches the declared schema", False, str(exc).splitlines()[0],
                 fix=(
                     f"rm {warehouse_path} and re-run. It is generated from seed "
                     f"{seed}; nothing is lost. Until then every figure would be "
                     f"freshly computed from a warehouse the gold set cannot index "
                     f"into — live, timestamped, and wrong."
                 )),
            Step("gold set builds", False, "not attempted — the warehouse is stale",
                 fix="Fix the warehouse first."),
        )
    except Exception as exc:  # noqa: BLE001 - report, do not traceback at a cloner
        return (
            Step("warehouse builds", False, f"{type(exc).__name__}: {exc}",
                 fix="Remove warehouse.duckdb and re-run; it is generated from a seed."),
            Step("gold set builds", False, "not attempted — it needs the warehouse",
                 fix="Fix the warehouse first."),
        )
    built = Step("warehouse matches the declared schema", True,
                 f"{warehouse} carries every declared category and region (seed {seed})")

    try:
        items = build_gold(warehouse)
    except Exception as exc:  # noqa: BLE001 - as above
        return built, Step(
            "gold set builds", False, f"{type(exc).__name__}: {exc}",
            fix="A pattern stopped discriminating against this warehouse. See "
                "src/loopeng/gold/build.py for what the gates mean.",
        )

    summary = clustering_summary(items)
    return built, Step(
        "gold set builds", True,
        f"{summary['n_items']} items in {summary['n_clusters']} clusters "
        f"({summary['items_per_cluster']} per cluster — not independent trials)",
    )


def check_rule_surface() -> Step:
    """The two-column result: what the verifier accepts, and what it rejects.

    Offline and free. A verifier that rejects nothing produces a wonderful pass rate,
    so both columns are reported and both have to be full.
    """
    report = run_probes()
    total = report["n_rules"]
    caught = total - report["n_missed_violations"]
    accepted = total - report["n_false_rejections"]
    ok = report["n_sound"] == total
    return Step(
        "rule surface (offline, free)", ok,
        f"rejects {caught}/{total} rule-breaking queries, "
        f"accepts {accepted}/{total} rule-honouring ones",
        fix=None if ok else "The verifier is not enforcing what it claims to. See "
                            "src/loopeng/verify/probes.py for the failing rule(s): "
                            + ", ".join(
                                rule for rule, r in report["by_rule"].items()
                                if not r["sound"]
                            ),
    )


def run(*, client_for=None) -> Preflight:
    """Every check, in order, with the network ones skipped when a key is absent.

    `client_for` is a callable taking a role and returning that role's client, not a
    single client. The three roles no longer share a vendor, so one client cannot
    serve them all — an OpenAI client handed the judge would fail on a surface it
    does not have. Defaults to building each one from the registry.
    """
    result = Preflight()

    key_step = result.add(check_key())
    if key_step.ok:
        settings = load_settings()
        for role in sorted(REGISTRY):
            step = _skip_optional_role(role, settings)
            if step is not None:
                result.add(step)
                continue
            client = client_for(role) if client_for else None
            result.add(check_model(role, client=client, ledger=result.ledger))
        warehouse_path, seed = settings.warehouse_path, settings.warehouse_seed
    else:
        result.add(Step(
            "models reachable", False, "not attempted — there is no key to call with",
            fix=f"Set {_required_vars()} first; the offline checks below still ran.",
        ))
        # Read off the Settings class rather than retyped, because instantiating it is
        # what just failed. A second copy of the defaults here would drift from the
        # real ones and mislead exactly the person who most needs these lines to pass.
        fields = Settings.model_fields
        warehouse_path = fields["warehouse_path"].default
        seed = fields["warehouse_seed"].default

    built, gold = check_warehouse_and_gold(warehouse_path=warehouse_path, seed=seed)
    result.add(built)
    result.add(gold)
    result.add(check_rule_surface())
    return result


def render(result: Preflight) -> str:
    lines = ["PREFLIGHT — the cheapest possible check that this checkout can spend", ""]
    lines += [step.render() for step in result.steps]
    lines += ["", f"cost of this preflight: {result.cost_line()}", ""]
    if result.ok:
        lines += [
            "Everything the sweep needs is in place. Next, for a few cents:",
            f"    {NEXT_COMMAND}",
            "",
            "Then render the charts with your run beside the committed baseline:",
            "    uv run python demos/04_hill_climbing_loop/charts.py",
        ]
    else:
        lines += ["Fix the FAIL line(s) above and run this again. Nothing has been spent "
                  "on a sweep yet."]
    return "\n".join(lines)
