"""The interface Phase 2's verifiers are built against.

Defined in Phase 0, and tested in Phase 0, because declaring a type without the
test that enforces its contract is precisely the declared-versus-enforced defect
this workshop is about — applied to our own foundation.

A verifier sees the question, the SQL, the schema, the declared rules, and what
happened when the SQL ran. It never sees the gold answer.
"""

import re
from dataclasses import dataclass

# A cheap structural guard, not a proof. It catches the obvious regression — a
# future author adding `gold_rows` to the context because it was convenient — and
# it catches it at the moment the field is added rather than after the numbers
# have already been reported. It cannot catch a field named `payload` that happens
# to carry the answer, so Phase 2's construction site has to stay honest too.
FORBIDDEN_FIELD_PATTERN = re.compile(r"gold|expected|answer|truth|reference", re.IGNORECASE)


@dataclass(frozen=True)
class VerifyContext:
    question: str
    sql: str
    schema_ddl: str
    rules: tuple[str, ...]
    attempt: int
    execution_rows: tuple[tuple, ...] | None
    execution_error: str | None
