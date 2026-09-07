"""The registry is the model policy, so these tests are the policy's enforcement.

Three roles, and the split between them is the session's argument: a budget agent that
runs every loop and every retry, a frontier reference that runs one bare arm, and a
judge from a different lab that never gates. If any of those three properties stops
holding, the claim the session makes stops being supported — so each one is asserted
here rather than left to the docstring that describes it.
"""

import pytest

from loopeng.registry import (
    ANTHROPIC,
    OPENAI,
    PROVIDER_KEY_VARS,
    REGISTRY,
    SCORING_ROLES,
    ModelVersionMismatch,
    assert_served_by,
    key_variable_for_role,
    spec_for,
)


def test_the_three_roles_are_agent_reference_and_judge():
    assert set(REGISTRY) == {"agent", "reference", "judge"}


def test_every_role_declares_its_own_name():
    """A spec that disagrees with its key would make every log line ambiguous."""
    for role, spec in REGISTRY.items():
        assert spec.role == role


def test_model_ids_carry_no_date_suffix():
    """Date-suffixed IDs are a recurring copy-paste error and 404 at request time.

    The *served* model often IS a dated snapshot — that is what gets recorded in
    provenance — but what we REQUEST is the stable id. See `assert_served_by`.
    """
    for spec in REGISTRY.values():
        assert "-20" not in spec.model_id


def test_no_model_id_is_a_floating_alias():
    """`-latest` and friends can be repointed by the vendor between two cells of one
    sweep. Every comparison in the run would then be a mixture of two models, and
    nothing on any chart would look wrong."""
    for spec in REGISTRY.values():
        assert not spec.model_id.endswith(("-latest", "-preview", "-newest"))


# ---- the argument: cheap agent, frontier bar, independent judge -------------


def test_the_agent_is_the_budget_tier_and_the_reference_is_not():
    """If the agent ever escalated to the reference model, "cheap plus loops matches
    frontier bare" would be measuring something else entirely."""
    from loopeng.pricing import prices_for

    agent = prices_for(REGISTRY["agent"].model_id)
    reference = prices_for(REGISTRY["reference"].model_id)
    assert agent.input < reference.input
    assert agent.output < reference.output


def test_the_judge_comes_from_a_different_lab_than_both_scoring_arms():
    """The standing objection to an LLM judge is that one from the same family as the
    thing being judged is not an independent check. Both scoring arms are OpenAI; if
    the judge ever became OpenAI too, the objection would apply to us."""
    assert REGISTRY["judge"].provider == ANTHROPIC
    for role in SCORING_ROLES:
        assert REGISTRY[role].provider == OPENAI
        assert REGISTRY[role].provider != REGISTRY["judge"].provider


def test_the_judge_is_not_a_scoring_role():
    """It triages and sorts failures. It never produces a cell's outcome."""
    assert "judge" not in SCORING_ROLES
    assert set(SCORING_ROLES) == {"agent", "reference"}


def test_the_two_scoring_arms_share_a_vendor():
    """C vs D is supposed to isolate the loops. If the arms came from different labs
    it would be confounded with a change of lab, which is a different experiment."""
    assert REGISTRY["agent"].provider == REGISTRY["reference"].provider


# ---- request kwargs: the differences that are 400s, not warnings -------------


def test_neither_scoring_role_pins_a_sampling_parameter():
    """Both are reasoning models and both reject a non-default `temperature` with a
    400. This is a real loss — every interval now carries run-to-run variance — and
    it is symmetric, which is what makes C vs D legitimate at all."""
    for role in SCORING_ROLES:
        for banned in ("temperature", "top_p", "top_k"):
            assert banned not in REGISTRY[role].request_kwargs


def test_the_judge_pins_temperature_because_it_can():
    """A triage label that moves between runs makes one failure look like two."""
    assert REGISTRY["judge"].request_kwargs["temperature"] == 0


def test_the_scoring_roles_pin_a_seed_instead():
    """Best-effort rather than a guarantee, which is why the residual disagreement is
    measured rather than assumed away — but it is what the vendor offers."""
    for role in SCORING_ROLES:
        assert "seed" in REGISTRY[role].request_kwargs


def test_the_scoring_roles_use_max_completion_tokens_not_max_tokens():
    """`max_tokens` is deprecated on this family and rejected on reasoning models."""
    for role in SCORING_ROLES:
        kwargs = REGISTRY[role].request_kwargs
        assert "max_completion_tokens" in kwargs
        assert "max_tokens" not in kwargs


def test_the_judge_uses_max_tokens_because_that_is_its_vendors_name_for_it():
    kwargs = REGISTRY["judge"].request_kwargs
    assert "max_tokens" in kwargs
    assert "max_completion_tokens" not in kwargs


def test_the_agent_spends_nothing_on_reasoning():
    """Writing a SELECT against a schema in the prompt is not a reasoning task, and
    reasoning tokens on every retry of every cell is the largest avoidable line in the
    agent's bill."""
    assert REGISTRY["agent"].request_kwargs["reasoning_effort"] == "none"


def test_the_reference_is_not_handicapped():
    """The bar has to be the model as it would actually be deployed. Capping its
    effort to save money would make the comparison flattering rather than
    informative."""
    assert "reasoning_effort" not in REGISTRY["reference"].request_kwargs


def test_the_reference_has_headroom_for_reasoning_plus_the_query():
    """The cap covers both together, so a budget sized for a SELECT truncates
    mid-thought."""
    assert (
        REGISTRY["reference"].request_kwargs["max_completion_tokens"]
        > REGISTRY["agent"].request_kwargs["max_completion_tokens"]
    )


def test_every_role_explains_why_it_holds_its_role():
    """The note reaches the run summary and the provenance block, so the reason
    travels with the number instead of living only in the registry."""
    for spec in REGISTRY.values():
        assert spec.note and len(spec.note) > 40


# ---- the silent-model-swap check --------------------------------------------


def test_a_dated_snapshot_of_the_requested_model_is_accepted_and_recorded():
    """`gpt-5.6-luna` is what we ask for; a dated snapshot is often what answers. The
    snapshot is the more precise fact, so it is the one that reaches provenance."""
    spec = spec_for("judge")
    served = assert_served_by(spec, f"{spec.model_id}-20251001")
    assert served == f"{spec.model_id}-20251001"


def test_a_different_model_raises_rather_than_being_recorded():
    """A silent swap mid-session would invalidate every comparison in the run and
    nothing on any chart would look wrong. That is the worst failure shape here,
    because it is undetectable after the fact."""
    with pytest.raises(ModelVersionMismatch) as caught:
        assert_served_by(spec_for("agent"), "gpt-4o-mini")
    assert "gpt-5.6-luna" in str(caught.value)
    assert "gpt-4o-mini" in str(caught.value)


def test_a_client_that_reports_no_model_is_not_treated_as_a_swap():
    """The offline suite substitutes clients everywhere. Refusing a missing model
    field would make this check impossible to exercise without a network."""
    assert assert_served_by(spec_for("agent"), None) == "gpt-5.6-luna"


# ---- credentials -------------------------------------------------------------


def test_each_role_names_the_variable_its_credential_comes_from():
    assert key_variable_for_role("agent") == "OPENAI_API_KEY"
    assert key_variable_for_role("judge") == "ANTHROPIC_API_KEY"


def test_the_variable_names_match_what_pydantic_derives_from_the_settings_fields():
    """The two spellings are mechanically linked — pydantic builds the env var from
    the field name — so they can drift apart silently. Every failure message a user
    reads names the variable, so the wrong one sends them to the wrong line of .env."""
    from loopeng.settings import Settings

    fields = set(Settings.model_fields)
    for provider, variable in PROVIDER_KEY_VARS.items():
        assert variable.lower() in fields, (
            f"{provider} is documented as {variable} but Settings has no matching field"
        )


# ---- immutability ------------------------------------------------------------


def test_request_kwargs_are_not_mutable():
    with pytest.raises(TypeError):
        REGISTRY["agent"].request_kwargs["max_completion_tokens"] = 1


def test_registry_itself_is_not_mutable():
    with pytest.raises(TypeError):
        REGISTRY["agent"] = None


def test_unknown_role_raises_and_names_what_exists():
    with pytest.raises(KeyError) as caught:
        spec_for("nope")
    assert "agent" in str(caught.value)
