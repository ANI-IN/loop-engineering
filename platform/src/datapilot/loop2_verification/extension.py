"""Extension points of Assignment 2: Verification loop, two more graders.

The verification loop calls both hooks on every run. They return no graders here, so class runs
are unchanged; the assignment adds a grader module for each and registers it below
(section-2-verification-loop/assignment/starter/README.md). The course build's boundary test keeps
this file in this state on the class branch.

What each kind of grader receives (a datapilot.contracts.GraderContext):
- a question grader runs once, before the analyst's first model call: question, knowledge_version,
  and extra["knowledge"] (the active KnowledgeVersion). A result with severity BLOCK ends the run
  with status needs_clarification: its feedback_for_agent becomes the clarifying question.
- an answer grader runs with the final-answer grader on every answer envelope: question, sql,
  result, answer, knowledge_version, and extra["approved"] (True once a person approved this run)
  and extra["export"]. A result with severity BLOCK goes back to the analyst as feedback, within
  the retry cap.
"""

from __future__ import annotations

from datapilot.contracts import Grader


# EXTENSION POINT, TODO 3 (verification-loop-3): register the new graders, in stage order.
def question_graders() -> list[Grader]:
    # EXTENSION POINT, TODO 1 (verification-loop-1): a new module in graders/ for the grader that
    # reads the question and the active knowledge version, returned here.
    return []


def answer_graders() -> list[Grader]:
    # EXTENSION POINT, TODO 2 (verification-loop-2): a new module in graders/ for the grader that
    # reads the final answer text, returned here.
    return []
