"""What used to be Harbor & Pine in code now comes from the selected pack: the router's keyword
table and digest question, and the personal data grader's wording (zero tokens, no database)."""

from __future__ import annotations

from datapilot.config import pack_config
from datapilot.contracts import GraderContext
from datapilot.loop1_agent.catalog import CatalogSnapshot
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop2_verification.graders import PersonalDataGrader
from datapilot.loop3_events import router

TEMPLATE = "_template"


def test_the_router_reads_the_selected_packs_keywords(select_pack) -> None:
    select_pack(TEMPLATE)
    families = pack_config()["autonomy"]["metric_families"]
    assert router.metric_family("How many members live in the north?", {}, families) == "members"
    assert router.metric_family("How many charges in June 2025?", {}, families) == "payments"
    assert router.metric_family("Net revenue in March 2025?", {}, families) == "revenue"
    assert router.metric_family("How many orders?", {}, families) is None


def test_the_class_pack_keeps_its_keywords(select_pack) -> None:
    select_pack("datapilot_us")
    assert [family for _, family in router.family_keywords()] == [
        "aov",
        "revenue",
        "orders",
        "customers",
        "products",
    ]


def test_the_digest_question_comes_from_the_pack(select_pack) -> None:
    select_pack("datapilot_us")
    assert router.digest_question("2026-01-30") == (
        "Give the daily KPI digest for 2026-01-30: net revenue, number of orders, and average "
        "order value, in one short paragraph."
    )
    select_pack(TEMPLATE)
    question = router.question_for("digest.requested", {"day": "2025-06-30"})
    assert question.startswith("Give the daily digest for 2025-06-30:") and "charges" in question


def test_a_blocked_export_names_the_packs_own_table(select_pack) -> None:
    select_pack(TEMPLATE)
    grader = PersonalDataGrader(VerificationConfig.from_pack(), CatalogSnapshot("club", {}))
    context = GraderContext(question="", sql="SELECT email FROM members", extra={"export": True})
    found = grader.check(context)
    assert not found.passed
    assert found.reason == "a marketing export reads the base table members"
    assert "club.members_marketable" in (found.feedback_for_agent or "")
