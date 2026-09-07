"""Provenance: what a cell carries so a chart can refuse to mix two experiments.

**The failure this guards has no visible symptom.** A figure rendered from cells
measured against different gold sets, or different prompts, produces bars, intervals
and a p-value — every one computed correctly, comparing two different experiments.
Nothing about the image says so, and no reader could tell.

That is why the refusal is in the render path rather than in a checklist.
"""

import pytest

from loopeng.sweep.fingerprint import (
    COMPARABLE_FIELDS,
    FINGERPRINT_FIELD,
    INPUT_FIELDS,
    IncomparableCells,
    RunFingerprint,
    assert_comparable,
    model_versions,
    prompt_digest,
    unverifiable_count,
)


class _Item:
    item_id, question, gold_sql, gold_rows = "a", "q", "SELECT 1", [[1]]


def _stamped(key, **overrides):
    stamp = RunFingerprint.for_run([_Item()], warehouse_seed=1).as_dict()
    stamp.update(overrides)
    return {"key": key, FINGERPRINT_FIELD: stamp}


# ---- what is in the stamp ----------------------------------------------------


def test_the_prompt_is_part_of_the_fingerprint():
    """The prompts are built from semantic_model.yaml, so a rule edited there changes
    what the model is told without changing the gold set or the code that reads it."""
    assert "prompt_sha256" in INPUT_FIELDS
    fingerprint = RunFingerprint.for_run([_Item()])
    assert fingerprint.prompt_sha256 == prompt_digest()
    assert len(fingerprint.prompt_sha256) == 64


def test_the_prompt_digest_moves_when_a_rule_changes(monkeypatch):
    """The property the hash exists for. If it did not move, it would be decoration."""
    import loopeng.prompts as prompts

    before = prompt_digest()
    monkeypatch.setattr(prompts, "render_prompt",
                        lambda level: f"{level}: a different instruction entirely")
    assert prompt_digest() != before


def test_the_exact_served_model_is_recorded_not_the_alias():
    """`assert_served_by` accepts a dated snapshot of the id we asked for and returns
    the snapshot, because the snapshot is the more precise fact. A silent reroute from
    one snapshot to another is visible in no other place."""
    served = {"agent": "gpt-5.6-luna-2026-08-01"}
    assert model_versions(served)["agent"] == "gpt-5.6-luna-2026-08-01"


def test_every_role_is_recorded_even_before_anything_answered():
    """A fingerprint minted before the first call is still comparable on everything
    else, so it falls back to the requested id rather than omitting the role."""
    from loopeng.registry import REGISTRY

    assert set(model_versions()) == set(REGISTRY)


# ---- the refusal --------------------------------------------------------------


def test_cells_measured_against_different_gold_sets_are_refused():
    cells = [_stamped("a"), _stamped("b", gold_sha256="f" * 64)]
    with pytest.raises(IncomparableCells) as caught:
        assert_comparable(cells)
    assert "gold set" in str(caught.value)
    assert "two different experiments" in str(caught.value)


def test_cells_measured_against_different_prompts_are_refused():
    cells = [_stamped("a"), _stamped("b", prompt_sha256="e" * 64)]
    with pytest.raises(IncomparableCells) as caught:
        assert_comparable(cells)
    assert "prompt" in str(caught.value)


def test_the_refusal_names_which_cells_disagree():
    """An operator needs to know which to re-run, not that something is wrong."""
    cells = [_stamped("agent_L0"), _stamped("agent_L3", gold_sha256="f" * 64)]
    with pytest.raises(IncomparableCells) as caught:
        assert_comparable(cells)
    assert "agent_L0" in str(caught.value) and "agent_L3" in str(caught.value)


def test_a_different_price_table_is_not_a_refusal():
    """Deliberately narrower than the run fingerprint. A price change moves the cost
    column and leaves every outcome alone; only the gold set and the prompt change
    what "correct" MEANS."""
    assert set(COMPARABLE_FIELDS) == {"gold_sha256", "prompt_sha256"}
    assert_comparable([_stamped("a"), _stamped("b", prices_taken_on="1999-01-01")])


def test_a_different_code_revision_is_not_a_refusal():
    """It may be a comment."""
    assert_comparable([_stamped("a"), _stamped("b", code_revision="deadbeef")])


def test_an_unstamped_cell_is_unverifiable_rather_than_refused():
    """The field is additive. Treating absence as a mismatch would make the guard fire
    on age rather than on disagreement — and absence is a different fact from wrong,
    so it is counted and reported instead."""
    cells = [_stamped("a"), {"key": "old"}]
    assert_comparable(cells)
    assert unverifiable_count(cells) == 1


def test_the_chart_writer_refuses_before_drawing_anything(tmp_path):
    """In the render path, not in a checklist. A checklist line is not enforcement —
    which is the defect this whole project is about."""
    from loopeng.sweep.charts import write_charts

    cells = [
        {**_stamped("a"), "label": "a", "role": "agent", "level": "L0",
         "mode": "loop", "replicate": 0, "complete": False, "rate_value": None,
         "rate_ci_low": None, "rate_ci_high": None, "rate_n": 0,
         "silent_error_rate": "not yet measured",
         "cost_usd": {"value": 0.0, "source": "estimated"}, "tokens": {}},
    ]
    odd = {**cells[0], **_stamped("b", gold_sha256="f" * 64), "label": "b"}

    with pytest.raises(IncomparableCells):
        write_charts([*cells, odd], tmp_path / "charts")
    assert not (tmp_path / "charts").exists() or not list(
        (tmp_path / "charts").glob("*.png")
    ), "nothing may be written before the refusal"


def test_a_fingerprint_survives_a_json_round_trip():
    """It is written as JSON and read back to decide whether a resumed sweep is the
    same run, so a field that changes container type in transit breaks resume.

    `models` was a tuple of pairs. JSON has no tuples, so it came back as a list of
    lists and never compared equal to a freshly built one — every resume would have
    minted a new run id and every freeze refused, for a difference that is only a
    container type and nothing a reader would ever see.
    """
    import json

    original = RunFingerprint.for_run([_Item()], warehouse_seed=1)
    restored = json.loads(json.dumps(original.as_dict()))

    for field_name in INPUT_FIELDS:
        assert restored[field_name] == original.as_dict()[field_name], field_name
