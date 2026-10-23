"""Grader 1, parse: the text is exactly one statement that sqlglot understands.

Fails closed: a parse error, a second statement, or sqlglot's opaque Command fallback (DO blocks,
EXPLAIN ANALYZE, CALL, VACUUM, PREPARE) all stop the query here.
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp

from datapilot.contracts import GraderContext, GraderResult, Stage
from datapilot.loop2_verification.graders._sql import blocked, parse_all, passed


class ParseGrader:
    name = "parse"
    stage = Stage.PRE_EXECUTION

    def check(self, context: GraderContext) -> GraderResult:
        text = (context.sql or "").strip()
        if not text:
            return blocked(self.name, "no SQL", "Send one SELECT statement.")
        try:
            statements = parse_all(text)
        except sqlglot.errors.ParseError as error:
            first = str(error).splitlines()[0]
            return blocked(self.name, f"parse error: {first}", f"The SQL does not parse: {first}")
        if len(statements) != 1:
            return blocked(
                self.name,
                f"{len(statements)} statements",
                "Send exactly one statement: a single SELECT, with no semicolon-separated parts.",
            )
        if isinstance(statements[0], exp.Command):
            return blocked(
                self.name,
                "unsupported syntax (parsed as an opaque command)",
                "Use a plain SELECT; this statement type is not allowed.",
            )
        return passed(self.name, "one statement")
