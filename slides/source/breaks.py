"""The two breaks and the poll, one slide each, at their fixed clock times under the third
rebuild's plan (.dev/review/deck3-brief.md, "Breaks and poll"): the first break 1:55-2:05, the poll
2:48-2:53, the second break 2:53-3:03. Each is copied from the reference deck (its slides 32 and
53), its text word for word; both breaks are 10 minutes, so both take the reference's 10-minute
timer. Short notes form (Purpose, What to say, Do lines, Transition); the Do lines name the
instructor's commands, so allow_commands is on.

The poll asks the owner's question (specification of 27 October 2026, section 4, item 9): "Which of
the four loops does your production agent have today?", with the four loops and "None"; under
design system 3 its question is drawn under the title. Its two counts are read back at Section 4's
agenda and again in the closing, on the slide "Which loop when: Match the loop to the failure".
"""

RULES = "design system 3"

BREAK_TITLE = "Time for a Break"
BREAK_TEXT = (
    "A 10-minute break is starting now. Please return when the timer ends to continue "
    "the presentation"
)
POLL_TITLE = "Live Zoom Poll"
POLL_TEXT = "We are launching a poll on Zoom. Please take 2 minutes to fill out the form."
POLL_QUESTION = "Which of the four loops does your production agent have today?"
POLL_OPTIONS = ("Agent loop", "Verification loop", "Event loop", "Hill-climbing loop", "None")
READ_BACK = "Which loop when: Match the loop to the failure"

BLOCKS = {
    "break1": [
        dict(
            kind="break",
            title=BREAK_TITLE,
            minutes=10,
            says=BREAK_TEXT,
            src="the reference deck, slide 32; docs/instructor-guide.md, Break",
            allow_commands=True,
            on_slide=[BREAK_TITLE, BREAK_TEXT],
            notes=[
                "Purpose: Give a 10-minute break after Section 2: Verification loop, and get the "
                "event loop ready for Section 3.",
                "What to say: Time for a 10-minute break. I will write the return time in the "
                "chat now. Questions you post during the break are answered when we return.",
                "Do: Write the return time, the local time 10 minutes from now, in the chat.",
                "Do: Reset the event loop during the break, so Section 3 starts clean: make reset "
                "NAME=event-loop.",
                "Do: Read Tokens today on the console's status line and note it.",
                "Transition: Welcome back. Wrong answers are now held while someone watches; "
                "next, running the agent from events with nobody watching: the event loop.",
            ],
        )
    ],
    "poll": [
        dict(
            kind="poll",
            title=POLL_TITLE,
            minutes=5,
            says=POLL_QUESTION,
            src="the reference deck, slide 53; docs/instructor-guide.md, Poll; the owner's "
            "specification of 27 October 2026, section 4, item 9",
            allow_commands=True,
            on_slide=[POLL_TITLE, POLL_TEXT, f"Question: {POLL_QUESTION}"],
            notes=[
                "Purpose: Ask which of the four loops learners' production agents have today; the "
                f"closing reads its two counts back on {READ_BACK}.",
                "What to say: One poll before the break. Which of the four loops does your "
                "production agent have today? Choose every one that applies: the agent loop, the "
                "verification loop, the event loop, the hill-climbing loop, or none. You have two "
                "minutes. Here is the result. Hold on to it: in the closing we match it to "
                "the failures each loop fixes.",
                "Do: Before you launch the poll, start the class session's baseline experiment: "
                "Improve > Run experiment on the active version, or make demo "
                "NAME=improve-baseline-experiment. The console accepts no baseline from another "
                "session, so never skip this step.",
                f"Do: Launch the Zoom poll with the question '{POLL_QUESTION}', multiple choice, "
                "and the options " + ", ".join(POLL_OPTIONS) + ".",
                "Do: Share the result, then note two counts: how many chose the hill-climbing "
                "loop, and how many chose none. Both are read back at Section 4's agenda and "
                f"again in the closing, on the slide {READ_BACK}.",
                "Do: Check that the benchmark progress strip on the run board is counting up.",
                "Transition: A 10-minute break now; the experiments keep running through it.",
            ],
        )
    ],
    "break2": [
        dict(
            kind="break",
            title=BREAK_TITLE,
            minutes=10,
            says=BREAK_TEXT,
            src="the reference deck, slide 32 (both breaks are 10 minutes); "
            "docs/instructor-guide.md, Break",
            allow_commands=True,
            on_slide=[BREAK_TITLE, BREAK_TEXT],
            notes=[
                "Purpose: Give a 10-minute break while the baseline experiment runs, and queue "
                "the naive analyzer for Section 4.",
                "What to say: Time for a 10-minute break. I will write the return time in the "
                "chat now. The experiments keep running while we are away, so Section 4 starts "
                "with real results.",
                "Do: Write the return time, the local time 10 minutes from now, in the chat.",
                "Do: At the start of the break, queue the naive analyzer and its candidate "
                "experiment behind the baseline: make demo NAME=improve-naive-analyzer-blocked "
                "PLANTED=1, or Improve > Run the naive analyzer (planted). Its verdict took 211 to "
                "580 seconds from the trigger in its 6 measured runs, so both experiments are "
                "usually finished when Section 4 opens.",
                "Do: Check once that the benchmark progress strip on the run board is counting up.",
                "Transition: Welcome back. Now the loop that makes the answer right: the "
                "hill-climbing loop.",
            ],
        )
    ],
}
