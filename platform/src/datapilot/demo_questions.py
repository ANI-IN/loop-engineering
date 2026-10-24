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
