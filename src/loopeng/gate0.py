"""Assembles results/gate0.json.

Every value carries `how` — the method that produced it — because a number whose
provenance is not written down becomes a number someone quotes later without the
caveat. Dollars carry `source: estimated` and never lose it.
"""

import json
import statistics
import time
from collections import Counter
from pathlib import Path

from loopeng.gold.build import ambiguity_summary, clustering_summary
from loopeng.gold.patterns import PATTERNS
from loopeng.pricing import PRICES_SOURCE, PRICES_TAKEN_ON
from loopeng.warehouse.connect import run_sql
from loopeng.warehouse.generate import content_checksum, generate

TEMPLATING_DISCLOSURE = (
    "Questions are templated: 10 patterns x 5 parameterisations. That caps how far "
    "these numbers generalise to freely-phrased questions, and it is stated on screen "
    "rather than left in a footnote."
)

# Measured, and recorded so the asymmetry is not misread later as a cost confound.
CACHING_IS_IMMATERIAL = (
    "Caching is MEASURED AS IMMATERIAL at this prompt size, and the Haiku/Sonnet "
    "asymmetry is NOT a cost confound. It fires in exactly one cell of eight "
    "(Sonnet L3, 1037 tokens against a 1024 minimum); Haiku's L3 is 648 against a "
    "4096 minimum and cannot cache at all. At prefixes of 286-1037 tokens the saving "
    "is trivial next to output tokens, especially with Sonnet's adaptive thinking on. "
    "Any Haiku-versus-Sonnet cost gap in the sweep is output tokens and thinking, not "
    "caching. Two consequences: sweep cell ordering is no longer load-bearing (the "
    "grouping is kept because it is tidier, not because anything depends on it), and "
    "Sonnet's 13-token margin is guarded by a test, since one trimmed rule sentence "
    "would silently drop the only cache that works."
)

# After the p09 deviation, refunds_net is carried by pattern 5 alone.
REFUNDS_NET_CAVEAT = (
    "refunds_net is exercised by ONE pattern only (p05_net_revenue, 5 items, 1 cluster). "
    "The sweep can therefore make no claim about that rule: with a single cluster there "
    "is no independent evidence, and the Phase 3 ablation will show it as unmeasurable "
    "for reasons that have nothing to do with the verifier under test. Read a flat "
    "refunds_net line as 'not measured here', not as 'the verifier missed it'. Rule "
    "enforcement is still covered by the Phase 2 rule-surface probes, which test the "
    "verifier directly rather than inferring it from sweep outcomes."
)


def _measured(value, how, **extra):
    return {"value": value, "how": how, **extra}


def warehouse_facts(path: Path, seed: int) -> dict:
    start = time.perf_counter()
    counts = generate(path, seed=seed)
    seed_seconds = time.perf_counter() - start

    twin = path.with_name("_gate0_twin.duckdb")
    generate(twin, seed=seed)
    byte_identical = path.read_bytes() == twin.read_bytes()
    content_identical = content_checksum(path) == content_checksum(twin)
    twin.unlink(missing_ok=True)

    return {
        "row_counts": _measured(counts, "COUNT(*) per table after generate()"),
        "seed_seconds": _measured(round(seed_seconds, 3), "perf_counter around generate()"),
        "db_file_bytes": _measured(path.stat().st_size, "Path.stat().st_size"),
        "content_identical_across_runs": _measured(
            content_identical, "SHA-256 over every table's sorted rows, two runs, same seed"
        ),
        "byte_identical_across_runs": _measured(
            byte_identical,
            "raw file bytes compared across two runs at the same seed",
            note=(
                "False. DuckDB writes non-deterministic file metadata, so the contract "
                "is content-identity, which the spec already stated. Kept in the report "
                "rather than dropped, because a later DuckDB making it true is worth noticing."
            ),
        ),
    }


def query_latency(items, warehouse: Path) -> dict:
    timings = []
    for item in items:
        start = time.perf_counter()
        run_sql(item.gold_sql, warehouse)
        timings.append((time.perf_counter() - start) * 1000)
    timings.sort()
    return {
        "n": len(timings),
        "p50_ms": _measured(
            round(statistics.median(timings), 2), "wall clock around run_sql, 50 gold SQLs"
        ),
        "p95_ms": _measured(
            round(timings[int(len(timings) * 0.95) - 1], 2),
            "wall clock around run_sql, 50 gold SQLs, 95th percentile",
        ),
        "max_ms": _measured(round(timings[-1], 2), "slowest of the 50 gold SQLs"),
    }


def rule_coverage(items) -> dict:
    per_rule_items = Counter(rule for item in items for rule in item.rules)
    per_rule_clusters = {
        rule: len({item.pattern_key for item in items if rule in item.rules})
        for rule in per_rule_items
    }
    single_cluster = sorted(rule for rule, n in per_rule_clusters.items() if n == 1)
    return {
        "by_pattern": {
            pattern.key: {
                "n_items": len(pattern.params),
                "rules": list(pattern.rules) or ["(none - the L0 floor)"],
            }
            for pattern in PATTERNS
        },
        "items_per_rule": dict(sorted(per_rule_items.items(), key=lambda kv: -kv[1])),
        "clusters_per_rule": dict(sorted(per_rule_clusters.items(), key=lambda kv: -kv[1])),
        "rules_carried_by_a_single_cluster": single_cluster,
        "caveat": REFUNDS_NET_CAVEAT,
    }


def build_report(
    *,
    items,
    warehouse: Path,
    seed: int,
    dataset,
    resumability: dict,
    rate_limits: dict,
    prompt_tokens: dict,
    cacheability_notes: list[str],
    ledger,
) -> dict:
    ambiguity = ambiguity_summary(items)
    return {
        "phase": "0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "warehouse": warehouse_facts(warehouse, seed),
        "query_latency": query_latency(items, warehouse),
        "gold_set": {
            "n_items": len(items),
            "clustering": clustering_summary(items),
            "templating_disclosure": TEMPLATING_DISCLOSURE,
            "rule_coverage": rule_coverage(items),
            "ambiguity": {
                "n_ambiguous_items": ambiguity["n_ambiguous_items"],
                "of_total": ambiguity["n_items"],
                "groups": ambiguity["groups"],
                "by_item": {k: [list(g) for g in v] for k, v in ambiguity["by_item"].items()},
                "how": (
                    "Naive variants compared pairwise per item with rows_equal. A collision "
                    "marks the item partial; it is never dropped or regenerated."
                ),
            },
        },
        "langsmith": {
            "dataset_url": dataset.get("url"),
            "dataset_id": dataset.get("dataset_id"),
            "resumability": resumability,
            "role": (
                "ADVISORY ONLY. results/*.json is the system of record. A test runs a cell "
                "with the LangSmith client stubbed to raise and asserts the results file is "
                "still complete and correct."
            ),
        },
        "prompts": {
            "token_counts": prompt_tokens,
            "findings": cacheability_notes,
            "how": "client.messages.count_tokens against each model; no inference run.",
            "caching_materiality": CACHING_IS_IMMATERIAL,
        },
        "rate_limits": {
            "observed": rate_limits,
            "how": (
                "One minimal request per model via .with_raw_response; every header matching "
                "'ratelimit' plus retry-after recorded verbatim. No loop toward a 429."
            ),
            "note": (
                "Pools are per-model. The two models report identical published ceilings, "
                "which is not the same as sharing a bucket - remaining counts and reset "
                "timestamps move independently, so Phase 3 still caps concurrency per model."
            ),
        },
        "spend": {
            "tokens": _measured(
                ledger.totals(), "usage fields read off every response, all four classes"
            ),
            "by_outcome": _measured(
                ledger.by_outcome(), "every call recorded, including failed and timed-out"
            ),
            "by_model": ledger.by_model(),
            "cost_usd": {
                "value": round(ledger.cost_usd(), 6),
                "source": "estimated",
                "how": (
                    f"measured token counts x a hand-entered price table "
                    f"(taken {PRICES_TAKEN_ON} from {PRICES_SOURCE}). Only a billing export "
                    "would make this a measurement, so the 'est.' label never comes off."
                ),
            },
        },
    }


def write_report(report: dict, path: Path = Path("results/gate0.json")) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return path
