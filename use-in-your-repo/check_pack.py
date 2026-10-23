"""Check a domain pack before DataPilot runs on it.

Usage, from the repository root:

    uv run python use-in-your-repo/check_pack.py [PACK] [--database]

PACK is a folder under platform/packs/ (default: _template). The checks read the pack's files
through the platform's own loaders and contracts, so a pack that passes loads the way the platform
loads it. With --database, every benchmark item with a naive query also runs its gold and naive
SQL through the read-only executor on both agent databases (DATABASE_URL_AGENT and
DATABASE_URL_AGENT_ALT in .env), and the naive query must give a different result: a trap that
changes no answer cannot catch a model. Then it runs the preflight data check
(preflight.data_check) as make preflight does. No model is called. `make check-pack PACK=<pack>`
runs it with --database.

Output: one line per check, "ok" or "x", then a summary. Exit code 1 when any check fails.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

from datapilot.config import PACKS
from datapilot.contracts import AnswerEnvelope, AnswerStatus, BenchmarkItem, Split
from datapilot.loop4_hill_climbing.pack_files import load_benchmark, load_knowledge
from datapilot.loop4_hill_climbing.preflight import DataCheck, PackHasNoPreflight, canary_ids

# The Harbor & Pine pack: the platform reads every key it has, so every pack needs each one.
REFERENCE_PACK = "datapilot_us"
STARTING_VERSION = "v1"


def key_paths(data: Any, prefix: str = "") -> Iterator[str]:
    """Every key path of a nested mapping, such as 'limits.row_cap'."""
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}{key}"
            yield path
            # Budget line names and price model names are the pack's own choice.
            if path not in {"build_budget.lines", "build_budget.session.lines", "prices"}:
                yield from key_paths(value, f"{path}.")


def listed(values: list[str]) -> str:
    """The values that failed a check, after the check's text; nothing when there are none."""
    return f": {', '.join(values)}" if values else ""


class Report:
    def __init__(self) -> None:
        self.problems = 0

    def check(self, ok: bool, what: str) -> bool:
        print(f"{'ok' if ok else 'x '} {what}")
        self.problems += 0 if ok else 1
        return ok


def check_config(pack: str, config: dict[str, Any], report: Report) -> None:
    reference = yaml.safe_load((PACKS / REFERENCE_PACK / "pack.yaml").read_text(encoding="utf-8"))
    missing = sorted(set(key_paths(reference)) - set(key_paths(config)))
    report.check(not missing, f"pack.yaml has every setting the platform reads{listed(missing)}")
    report.check(config.get("name") == pack, f"pack.yaml name is the folder name '{pack}'")
    schema = config.get("databases", {}).get("allowed_schema", "")
    report.check(bool(schema), f"databases.allowed_schema is set ('{schema}')")
    personal = config.get("personal_data", {})
    outside = [c for c in personal.get("columns", []) if c.split(".")[0] != schema]
    report.check(not outside, "every personal data column is in allowed_schema" + listed(outside))
    view = str(personal.get("marketing_view", ""))
    in_schema = view.split(".")[0] == schema
    report.check(in_schema, f"the marketing view is in the allowed schema ({view})")
    autonomy = config.get("autonomy", {})
    keyed = {str(row.get("family")) for row in autonomy.get("family_keywords") or []}
    unknown = sorted(keyed - set(autonomy.get("metric_families", [])))
    named = "each autonomy.family_keywords family is in autonomy.metric_families"
    report.check(not unknown, named + listed(unknown))
    digest = str(config.get("digest", {}).get("question", ""))
    report.check("{day}" in digest, "digest.question names the day as {day}")


def check_benchmark(pack: str, config: dict[str, Any], report: Report) -> list[BenchmarkItem]:
    try:
        items = load_benchmark(pack)
    except Exception as error:  # a validation error names the item and the field
        report.check(False, f"benchmark/*.yaml loads as BenchmarkItem: {error}")
        return []
    report.check(True, f"benchmark/*.yaml loads as BenchmarkItem ({len(items)} items)")
    ids = [item.id for item in items]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    report.check(not duplicates, f"benchmark item ids are unique{listed(duplicates)}")
    dev = [item for item in items if item.split is Split.DEV]
    holdout = [item for item in items if item.split is Split.HOLDOUT]
    report.check(bool(dev) and bool(holdout), f"{len(dev)} dev and {len(holdout)} holdout items")
    no_gold = [i.id for i in items if i.expected_status is AnswerStatus.ANSWERED and not i.gold_sql]
    report.check(not no_gold, f"every answered item has gold_sql{listed(no_gold)}")
    no_naive = [item.id for item in items if item.traps and not item.naive_sql]
    report.check(not no_naive, f"every trap item has naive_sql{listed(no_naive)}")
    families = set(config.get("autonomy", {}).get("metric_families", []))
    unknown = sorted({item.metric_family for item in items} - families)
    report.check(not unknown, "each metric_family is in autonomy.metric_families" + listed(unknown))
    rules_file = PACKS / pack / "benchmark" / "business_rules.md"
    rules = rules_file.read_text(encoding="utf-8") if rules_file.is_file() else ""
    report.check(bool(rules), "benchmark/business_rules.md exists")
    traps = sorted({trap for item in items for trap in item.traps})
    # A trap is named by its id, or by its id in words ("net_revenue" as "net revenue").
    unnamed = [t for t in traps if t not in rules and t.replace("_", " ") not in rules.lower()]
    named = f"business_rules.md names every trap ({', '.join(traps)})"
    report.check(not unnamed, named + listed(unnamed))
    return items


def check_preflight(config: dict[str, Any], items: list[BenchmarkItem], report: Report) -> None:
    try:
        data = DataCheck.from_pack(config)
        report.check(True, f"preflight.data_check reads {data.qualified}")
    except PackHasNoPreflight as error:
        report.check(False, f"preflight.data_check names a table: {error.args[0]}")
    try:
        canary = canary_ids(config)
    except PackHasNoPreflight as error:
        report.check(False, f"preflight.canary names the pack's own canary items: {error.args[0]}")
        return
    by_id = {item.id: item for item in items}
    easy, traps = canary["easy"], canary["traps"]
    report.check(
        len(easy) == 3 and all(i in by_id and not by_id[i].traps for i in easy),
        f"three easy canary items without traps {easy}",
    )
    report.check(
        len(traps) == 2 and all(i in by_id and by_id[i].traps for i in traps),
        f"two trap canary items {traps}",
    )


def check_database(pack: str, items: list[BenchmarkItem], report: Report) -> None:
    from datapilot.config import pack_config
    from datapilot.loop2_verification.config import VerificationConfig
    from datapilot.loop2_verification.executor import WarehouseRunner
    from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator
    from datapilot.loop4_hill_climbing.sql_runner import ReadOnlyRunner, executors

    config = VerificationConfig.from_pack(pack_config(pack, PACKS))
    evaluator = ExecutionEvaluator(runner=ReadOnlyRunner(WarehouseRunner(executors(config))))
    for item in items:
        if not item.gold_sql:
            continue
        gold = AnswerEnvelope(status=AnswerStatus.ANSWERED, final_sql=item.gold_sql)
        result = evaluator.evaluate(item, gold)
        report.check(result.passed, f"{item.id}: the gold query runs on both databases")
        if item.naive_sql:
            naive = AnswerEnvelope(status=AnswerStatus.ANSWERED, final_sql=item.naive_sql)
            result = evaluator.evaluate(item, naive)
            report.check(not result.passed, f"{item.id}: the naive query differs from gold")


def check_data(config: dict[str, Any], report: Report) -> None:
    """The preflight data check, as make preflight runs it: the agent's role sees rows."""
    try:
        found = DataCheck.from_pack(config).check()
    except PackHasNoPreflight:
        return  # already reported by check_preflight
    report.check(found.ok, f"preflight data check: {found.detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pack", nargs="?", default="_template", help="a folder in platform/packs/")
    parser.add_argument("--database", action="store_true", help="also run gold and naive SQL")
    args = parser.parse_args(argv)
    folder: Path = PACKS / args.pack
    if not (folder / "pack.yaml").is_file():
        print(f"x no pack.yaml in {folder}")
        return 1
    report = Report()
    config = yaml.safe_load((folder / "pack.yaml").read_text(encoding="utf-8"))
    check_config(args.pack, config, report)
    try:
        load_knowledge(STARTING_VERSION, args.pack)
        report.check(True, f"knowledge/{STARTING_VERSION}.yaml loads as KnowledgeVersion")
    except Exception as error:
        report.check(False, f"knowledge/{STARTING_VERSION}.yaml loads as KnowledgeVersion: {error}")
    items = check_benchmark(args.pack, config, report)
    check_preflight(config, items, report)
    if args.database and items:
        check_database(args.pack, items, report)
        check_data(config, report)
    print(f"check_pack: {args.pack}: {report.problems} problems")
    return 1 if report.problems else 0


if __name__ == "__main__":
    sys.exit(main())
