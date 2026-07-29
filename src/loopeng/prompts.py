"""The prompts whose token counts decide whether caching fires.

L0 gets the schema and nothing else. L3 gets the schema plus every rule statement
from `semantic_model.yaml`. The difference between them is the entire experiment:
if L0 also carried the rules, both levels would score the same and the dial chart
would measure nothing.

The rules are rendered from the YAML rather than written out here, so a rule added
to the semantic model reaches the L3 prompt without anyone remembering to copy it.
A rule that exists in one place and not the other is the declared-versus-enforced
defect again.
"""

from loopeng.warehouse.schema import SCHEMA_DDL, load_semantic_model

LEVELS = ("L0", "L3")

_HEADER = """You are a data analyst. Answer the question by writing a single DuckDB SQL query.

Schema:
{schema}"""

_RULES_HEADER = """
Business rules that apply to every query against this warehouse:

{rules}
"""

_FOOTER = """
Return only the SQL query, with no explanation."""


def render_rules() -> str:
    """Every rule statement from the semantic model, numbered, with its FX table."""
    model = load_semantic_model()
    lines = []
    for index, (name, rule) in enumerate(model["rules"].items(), start=1):
        statement = " ".join(rule["statement"].split())
        lines.append(f"{index}. [{name}] {statement}")

    factors = ", ".join(
        f"{currency} = {factor}" for currency, factor in sorted(model["usd_factor"].items())
    )
    lines.append(
        f"{len(lines) + 1}. [usd_factor] Multiply an amount in minor units by its "
        f"currency's factor to get USD: {factors}."
    )
    return "\n".join(lines)


def render_prompt(level: str) -> str:
    if level not in LEVELS:
        raise ValueError(f"unknown level {level!r}; expected one of {LEVELS}")

    prompt = _HEADER.format(schema=SCHEMA_DDL.strip())
    if level == "L3":
        prompt += "\n" + _RULES_HEADER.format(rules=render_rules())
    return prompt + _FOOTER
