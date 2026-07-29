import pytest

from loopeng.registry import REGISTRY, spec_for


def test_roles_are_exactly_worker_and_frontier():
    assert set(REGISTRY) == {"worker", "frontier"}


def test_model_ids_carry_no_date_suffix():
    """Date-suffixed IDs are a recurring copy-paste error and 404 at request time."""
    for spec in REGISTRY.values():
        assert "-20" not in spec.model_id


def test_worker_never_sends_effort():
    """output_config.effort errors on Haiku 4.5. This asymmetry is the whole reason
    the registry maps to a spec object rather than a bare string."""
    assert "output_config" not in REGISTRY["worker"].request_kwargs


def test_the_frontier_role_sends_no_sampling_params():
    """Non-default temperature/top_p/top_k are rejected on Sonnet 5 with a 400."""
    for banned in ("temperature", "top_p", "top_k"):
        assert banned not in REGISTRY["frontier"].request_kwargs


def test_the_worker_role_pins_temperature_to_zero():
    """Haiku accepts it and Sonnet does not, so only the worker is pinned.

    Measured justification, not preference: at default temperature two runs of the same
    50 items disagreed on 6 of the 45 the loop never touched — a 13.3% run-to-run floor
    that would swamp the sweep's pre-registered effect."""
    assert REGISTRY["worker"].request_kwargs["temperature"] == 0


def test_only_one_role_is_pinned_so_the_asymmetry_is_explicit():
    """If both were pinned, or neither, there would be no asymmetry to disclose. There
    is one, and every cross-model comparison has to carry it."""
    pinned = {role for role, spec in REGISTRY.items() if "temperature" in spec.request_kwargs}
    assert pinned == {"worker"}


def test_frontier_sends_no_thinking_key_so_adaptive_runs():
    """Omitting `thinking` on Sonnet 5 runs adaptive thinking. That is the intended
    deployment shape, not an oversight."""
    assert "thinking" not in REGISTRY["frontier"].request_kwargs


def test_frontier_has_headroom_for_thinking():
    """max_tokens caps thinking plus output text together, so a budget sized for a
    SELECT statement would truncate mid-thought."""
    frontier_max = REGISTRY["frontier"].request_kwargs["max_tokens"]
    worker_max = REGISTRY["worker"].request_kwargs["max_tokens"]
    assert frontier_max > worker_max


def test_no_role_sends_top_p_or_top_k():
    for spec in REGISTRY.values():
        for banned in ("top_p", "top_k"):
            assert banned not in spec.request_kwargs


def test_request_kwargs_are_not_mutable():
    with pytest.raises(TypeError):
        REGISTRY["worker"].request_kwargs["max_tokens"] = 1


def test_registry_itself_is_not_mutable():
    with pytest.raises(TypeError):
        REGISTRY["worker"] = None


def test_unknown_role_raises():
    with pytest.raises(KeyError):
        spec_for("nope")
