"""The two breaks and the poll, one slide each, at their fixed clock times: the first break
1:45-1:55, the poll 2:50-2:55, the second break 2:55-3:05. Short notes form (Purpose, What to
say, Do lines, Transition); the Do lines name the instructor's commands, so allow_commands is on.
"""

RULES = "design system"

BREAK_TITLE = "Time for a Break"
BREAK_TEXT = (
    "A 10-minute break is starting now. Please return when the timer ends to continue "
    "the presentation"
)
POLL_TITLE = "Live Zoom Poll"
POLL_TEXT = "We are launching a poll on Zoom. Please take 2 minutes to fill out the form."

BLOCKS = {
    "break1": [
        dict(
            kind="break",
            title=BREAK_TITLE,
            minutes=10,
            says=BREAK_TEXT,
            src="docs/instructor-guide.md, Break (1:45-1:55)",
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
                "Transition: Welcome back. Answers are now checked; next, who asks, when, and who "
                "may approve: the event loop.",
            ],
        )
    ],
    "poll": [
        dict(
            kind="poll",
            title=POLL_TITLE,
            minutes=5,
            says=POLL_TEXT,
            src="docs/instructor-guide.md, Poll (2:50-2:55)",
            allow_commands=True,
            on_slide=[POLL_TITLE, POLL_TEXT],
            notes=[
                "Purpose: Ask which autonomy level learners would grant, before Section 4 shows "
                "the evidence each level should need.",
                "What to say: One poll before the break: which autonomy level would you grant "
                "the revenue digest today, and why: the report-only level, the assisted level, or "
                "the unattended level? You have two minutes. Here is the result. Keep that answer "
                "in mind; Section 4: Hill-climbing loop reads it back against what revenue and "
                "orders actually earned.",
                "Do: Before you launch the poll, start the class session's baseline experiment: "
                "Improve > Run experiment on the active version, or make demo "
                "NAME=improve-baseline-experiment. The console accepts no baseline from another "
                "session, so never skip this step.",
                "Do: Launch the Zoom poll, then check that the benchmark progress strip on the "
                "run board is counting up.",
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
            src="docs/instructor-guide.md, Break (2:55-3:05)",
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
                "usually finished when Section 4 opens by reading them.",
                "Do: Check once that the grouped benchmark progress strip on the run board is "
                "counting up.",
                "Transition: Welcome back. The poll asked how much autonomy to grant; now we earn "
                "it, with the hill-climbing loop.",
            ],
        )
    ],
}
