import dataclasses

import pytest

from loopeng.contracts import FORBIDDEN_FIELD_PATTERN, VerifyContext


def _context(**overrides):
    base = {
        "question": "q",
        "sql": "SELECT 1",
        "schema_ddl": "",
        "rules": (),
        "attempt": 1,
        "execution_rows": None,
        "execution_error": None,
    }
    return VerifyContext(**{**base, **overrides})


def test_verify_context_cannot_reach_gold():
    """The single architectural contract of this project. A verifier that can see
    the answer makes every number in the workshop meaningless, so this is a test
    rather than a convention."""
    for field in dataclasses.fields(VerifyContext):
        assert not FORBIDDEN_FIELD_PATTERN.search(field.name), (
            f"VerifyContext.{field.name} could expose the answer to a verifier"
        )


def test_the_pattern_actually_matches_the_words_it_claims_to():
    """A guard regex that matches nothing would pass the test above while
    protecting nothing."""
    for word in ("gold", "expected", "answer", "truth", "reference"):
        assert FORBIDDEN_FIELD_PATTERN.search(f"some_{word}_field")


def test_the_pattern_is_case_insensitive():
    assert FORBIDDEN_FIELD_PATTERN.search("goldRows")
    assert FORBIDDEN_FIELD_PATTERN.search("EXPECTED_VALUE")


def test_the_pattern_does_not_match_innocent_names():
    """Over-matching would push a future author to rename a legitimate field into
    something obscure, or to delete the check."""
    for name in ("question", "sql", "schema_ddl", "rules", "attempt", "execution_rows"):
        assert not FORBIDDEN_FIELD_PATTERN.search(name)


def test_verify_context_is_frozen():
    context = _context()
    with pytest.raises(dataclasses.FrozenInstanceError):
        context.sql = "SELECT 2"


def test_carries_what_a_verifier_legitimately_needs():
    """The contract is about what a verifier must NOT see. It must still see
    enough to do its job: the question, the SQL, the schema, the declared rules,
    the attempt number, and what happened when the SQL ran."""
    context = _context(rules=("soft_delete",), execution_rows=((1, "a"),))
    assert context.question and context.sql
    assert context.rules == ("soft_delete",)
    assert context.execution_rows == ((1, "a"),)
    assert context.execution_error is None


def test_execution_error_and_rows_are_independently_expressible():
    """A failed execution has an error and no rows; a successful one has rows and
    no error. Both must be representable without a sentinel."""
    failed = _context(execution_rows=None, execution_error="syntax error at or near")
    assert failed.execution_error and failed.execution_rows is None
