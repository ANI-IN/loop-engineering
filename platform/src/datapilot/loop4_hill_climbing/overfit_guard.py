"""The overfit guard: a deterministic check after the critic. A proposed rule is rejected when it
quotes a benchmark question (a run of consecutive words shared with any question, dev or holdout)
or copies gold SQL (a run of consecutive SQL tokens shared with any gold query). Thresholds come
from pack.yaml (evaluation.overfit_question_words, evaluation.overfit_sql_tokens).

The promotion gate checks again: new_rule_flags names every rule a candidate version adds to the
active one that the guard rejects, so a version written without the guard (the naive analyzer)
is blocked whatever its holdout count.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from datapilot.config import pack_config
from datapilot.contracts import BenchmarkItem, KnowledgeVersion, ProposedRule

_WORD = re.compile(r"[a-z0-9]+")
_SQL_TOKEN = re.compile(r"'[^']*'|[a-z_][a-z0-9_]*|\d+(?:\.\d+)?|[^\s\w]")


def words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def sql_tokens(text: str) -> list[str]:
    return _SQL_TOKEN.findall(text.lower())


def ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


@dataclass(frozen=True)
class GuardResult:
    rule_id: str
    passed: bool
    reasons: list[str]


class OverfitGuard:
    def __init__(self, items: Sequence[BenchmarkItem], *, question_words: int, sql_tokens_run: int):
        self.question_words = question_words
        self.sql_tokens_run = sql_tokens_run
        self._questions = {
            gram: item.id for item in items for gram in ngrams(words(item.question), question_words)
        }
        self._gold = {
            gram: item.id
            for item in items
            if item.gold_sql
            for gram in ngrams(sql_tokens(item.gold_sql), sql_tokens_run)
        }

    @classmethod
    def from_pack(cls, items: Sequence[BenchmarkItem]) -> OverfitGuard:
        evaluation = pack_config()["evaluation"]
        return cls(
            items,
            question_words=evaluation["overfit_question_words"],
            sql_tokens_run=evaluation["overfit_sql_tokens"],
        )

    def check(self, rule: ProposedRule) -> GuardResult:
        reasons = []
        prose = " ".join([rule.title, rule.rule_text, rule.applies_when, rule.sql_guidance])
        quoted = sorted(
            {
                self._questions[g]
                for g in ngrams(words(prose), self.question_words)
                if g in self._questions
            }
        )
        if quoted:
            reasons.append(
                f"quotes benchmark questions ({self.question_words} or more words in a row): "
                + ", ".join(quoted)
            )
        text = " ".join([rule.rule_text, rule.sql_guidance])
        copied = sorted(
            {
                self._gold[g]
                for g in ngrams(sql_tokens(text), self.sql_tokens_run)
                if g in self._gold
            }
        )
        if copied:
            reasons.append(
                f"copies gold SQL ({self.sql_tokens_run} or more tokens in a row): "
                + ", ".join(copied)
            )
        return GuardResult(rule_id=rule.id, passed=not reasons, reasons=reasons)


def new_rule_flags(
    guard: OverfitGuard, candidate: KnowledgeVersion, active: KnowledgeVersion
) -> list[str]:
    """The ids of the rules the candidate adds or changes against the active version that the
    guard rejects, in the candidate's order; the active version's own rules are never checked."""
    have = {rule.id: rule for rule in active.rules}
    flagged = []
    for rule in candidate.rules:
        if have.get(rule.id) == rule:
            continue
        proposed = ProposedRule(**rule.model_dump(), expected_effect="")
        if not guard.check(proposed).passed:
            flagged.append(rule.id)
    return flagged
