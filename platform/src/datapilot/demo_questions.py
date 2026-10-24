"""The question each registry demo asks: the one source for `make demo NAME=`
(datapilot.loop3_events.demos) and for the console's buttons, so a demo started either way sends
the same words. Outside the loop packages, because the console never imports a loop package.
They are questions, never answers.
"""

from __future__ import annotations

SPINE_QUESTION = "What was our net revenue in fiscal year 2025?"
DEFAULT_QUESTION = "How many orders have been placed in total?"
WEBHOOK_QUESTION = "How many orders were placed yesterday?"
# The approval demo (events-approval-survives-restart) sends this as an export.requested event, not
# a question.asked one, so it stays out of QUESTIONS. Its query returns a personal-data column, so
# the run is held for human approval; this wording is the one verified live for that moment.
EXPORT_QUESTION = (
    "Export the California customers who may receive marketing, with their email addresses."
)

QUESTIONS = {
    "agent-simple-question": DEFAULT_QUESTION,
    "agent-texas-last-quarter": (
        "What was net revenue by product category for customers in Texas last fiscal quarter?"
    ),
    "agent-confident-wrong-answer": SPINE_QUESTION,
    "verify-graders-pass-still-wrong": SPINE_QUESTION,
    "events-webhook-question": WEBHOOK_QUESTION,
    # Both arrive as webhooks on the Events page: in the console, the duplicates button sends this
    # question three times, and the kill switch stops the run Send webhook question started.
    "events-duplicate-events": WEBHOOK_QUESTION,
    "events-kill-switch-in-flight": WEBHOOK_QUESTION,
    "improve-cleared-unattended": SPINE_QUESTION,
}


def question_for(demo_id: str) -> str:
    """The question demo `demo_id` sends; a demo with no question of its own asks the default."""
    return QUESTIONS.get(demo_id, DEFAULT_QUESTION)


# The demos the Agent page starts from a typed question: Agent > Ask is their registry trigger
# (the spine question also has its own button).
AGENT_ASK_DEMOS = (
    "agent-simple-question",
    "agent-texas-last-quarter",
    "agent-confident-wrong-answer",
)


def demo_asking(question: str, demo_ids: tuple[str, ...]) -> str | None:
    """The demo among `demo_ids` that asks `question` word for word (spaces around it ignored),
    or None: a typed question no demo asks is labelled as no demo, never as one it is not."""
    typed = question.strip()
    return next((d for d in demo_ids if QUESTIONS.get(d) == typed), None)
