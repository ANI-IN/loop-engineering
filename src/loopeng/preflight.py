"""Two cents' worth of checks, before anything expensive.

The smallest live path used to be `--profile delivery`: 4 cells, 50 items, ~200 calls,
projected est. $0.43. A first-time cloner had no way to spend a fraction of a cent
finding out whether their key was valid, whether both model ids resolved **on their
account**, and whether the warehouse and gold set built at all. They found out by
starting the thing that spends.

So this runs in order, prints pass/fail per line, and stops at the first failure that
makes the next check meaningless. Four properties are load-bearing:

**Each model is called with the request kwargs the registry declares.** Not a
simplified probe call. `temperature=0` is legal on Haiku and a 400 on Sonnet 5, and a
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
from loopeng.registry import REGISTRY
from loopeng.settings import MissingCredential, Settings, load_settings, require_api_key
from loopeng.usage import CallUsage, UsageLedger
from loopeng.verify.probes import run_probes
from loopeng.warehouse.connect import ensure_warehouse

log = structlog.get_logger(__name__)

KEY_VAR = "ANTHROPIC_API_KEY"

# Enough output for a model to say one word. Applied only where max_tokens is not also
# the thinking budget — see the module docstring.
PROBE_MAX_TOKENS = 16

PROBE_PROMPT = "Reply with the single word: ok"

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

    def render(self) -> str:
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


def check_key(settings=None) -> Step:
    """Is the one required credential present? Nothing else here works without it."""
    try:
        settings = settings or load_settings()
    except MissingCredential as exc:
        return Step(
            f"{KEY_VAR} is set", False, str(exc).splitlines()[0],
            fix=f"cp .env.example .env, then add {KEY_VAR}=<your key>. "
                f"LANGSMITH_API_KEY is optional and can stay empty.",
        )
    return Step(f"{KEY_VAR} is set", True, "present (value never printed or logged)")


def check_model(role: str, *, client, ledger: UsageLedger) -> Step:
    """One minimal call, with the registry's own kwargs. Records what it billed."""
    spec = REGISTRY[role]
    kwargs = dict(spec.request_kwargs)
    # Trimmed only where it is purely an output cap. On the frontier role max_tokens
    # also bounds adaptive thinking, and squeezing it there is how a preflight invents
    # a failure the sweep would never have hit.
    if role == "worker":
        kwargs["max_tokens"] = PROBE_MAX_TOKENS

    try:
        response = client.messages.create(
            model=spec.model_id,
            messages=[{"role": "user", "content": PROBE_PROMPT}],
            **kwargs,
        )
    except Exception as exc:  # noqa: BLE001 - the verdict IS the exception
        from loopeng.agent.loop import triage_call_failure

        _termination, message = triage_call_failure(exc, role=role, model_id=spec.model_id)
        ledger.record(CallUsage(spec.model_id, "error"))
        return Step(
            f"{role} model reachable ({spec.model_id})", False,
            f"the call was refused: {type(exc).__name__}", fix=message,
        )

    usage = ledger.record(CallUsage.from_response(spec.model_id, response))
    return Step(
        f"{role} model reachable ({spec.model_id})", True,
        f"answered with the registry's own kwargs "
        f"({usage.input_tokens} in, {usage.output_tokens} out)",
    )


def check_warehouse_and_gold(*, warehouse_path: Path, seed: int) -> tuple[Step, Step]:
    """Offline. Runs even when the key is bad, so a typo does not hide the rest."""
    try:
        warehouse = ensure_warehouse(warehouse_path, seed=seed)
    except Exception as exc:  # noqa: BLE001 - report, do not traceback at a cloner
        return (
            Step("warehouse builds", False, f"{type(exc).__name__}: {exc}",
                 fix="Remove warehouse.duckdb and re-run; it is generated from a seed."),
            Step("gold set builds", False, "not attempted — it needs the warehouse",
                 fix="Fix the warehouse first."),
        )
    built = Step("warehouse builds", True, f"{warehouse} verified from seed {seed}")

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


def run(*, client=None) -> Preflight:
    """Every check, in order, with the network ones skipped when the key is absent."""
    result = Preflight()

    key_step = result.add(check_key())
    if key_step.ok:
        settings = load_settings()
        if client is None:
            import anthropic

            client = anthropic.Anthropic(
                api_key=require_api_key(settings).get_secret_value()
            )
        for role in sorted(REGISTRY):
            result.add(check_model(role, client=client, ledger=result.ledger))
        warehouse_path, seed = settings.warehouse_path, settings.warehouse_seed
    else:
        result.add(Step(
            "models reachable", False, "not attempted — there is no key to call with",
            fix=f"Set {KEY_VAR} first; the offline checks below still ran.",
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
            "    uv run python demos/04_hill_climbing_loop/charts.py --reference=compare",
        ]
    else:
        lines += ["Fix the FAIL line(s) above and run this again. Nothing has been spent "
                  "on a sweep yet."]
    return "\n".join(lines)
