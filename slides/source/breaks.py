"""The two breaks and the poll."""

BREAK_TEXT = (
    "A 10-minute break is starting now. Please return when the timer ends to continue "
    "the presentation"
)
R = "<!-- refresh after the session: {} -->"

BLOCKS = {
    "break1": [
        {
            "kind": "break",
            "title": "Time for a Break",
            "layout": "blank",
            "minutes": 10,
            "says": "A 10-minute break is starting now. Please return when the timer ends to "
            "continue the presentation",
            "src": "-",
            "on_slide": [
                "Time for a Break",
                "A 10-minute break is starting now. Please return when the timer ends to "
                "continue the presentation",
            ],
            "notes": [
                "Say: Write the return time, 1:55, in the chat and on the slide.",
                "During the break, reset the event loop section so Section 3: Event loop "
                "starts clean.",
                "Point at: the timer.",
                'Likely question: "Can I run the demos now?" Answer: after class is better; '
                "your runs use your own key.",
                "Transition: Welcome back. Answers are now safe and bounded. Next: who "
                "asks, when, and who may approve.",
            ],
            "container": "fixed template slide",
        }
    ],
    "poll": [
        {
            "kind": "poll",
            "title": "Live Zoom Poll",
            "layout": "blank",
            "minutes": 5,
            "says": "We are launching a poll on Zoom. Please take 2 minutes to fill out the form.",
            "src": "docs/instructor-guide.md",
            "allow_commands": True,
            "on_slide": [
                "Live Zoom Poll",
                "We are launching a poll on Zoom. Please take 2 minutes to fill out the form.",
            ],
            "notes": [
                "Say: Before you launch the poll, start the baseline experiment on the "
                "Improve page so it runs through the break. It is the class session's "
                "baseline; the console accepts no baseline from another session.",
                "Instructor reference: Improve > Run experiment on the active version, or "
                "`make demo NAME=improve-baseline-experiment`.",
                'Then launch the poll: "Which autonomy level would you grant the revenue '
                'digest today, and why?" Options: the report-only level, the assisted level, '
                "the unattended level. Read the result aloud. Keep it for Section 4: "
                "Hill-climbing loop, which shows what evidence the unattended level should "
                "need.",
                "Point at: the poll window, then the benchmark progress strip on the run board.",
                'Likely question: "Is there a right answer?" Answer: without holdout '
                "evidence, the report-only or the assisted level; Section 4 shows how a "
                "metric family earns more.",
                "Transition: A 10-minute break; the baseline keeps running.",
            ],
            "container": "fixed template slide",
        }
    ],
    "break2": [
        {
            "kind": "break",
            "title": "Time for a Break",
            "layout": "blank",
            "minutes": 10,
            "says": "A 10-minute break is starting now. Please return when the timer ends to "
            "continue the presentation",
            "src": "-",
            "on_slide": [
                "Time for a Break",
                "A 10-minute break is starting now. Please return when the timer ends to "
                "continue the presentation",
            ],
            "notes": [
                "Say: Write the return time, 3:05, in the chat. Check once that the grouped "
                "benchmark progress strip on the run board is counting up.",
                "Point at: the timer.",
                'Likely question: "Will the experiment finish in time?" Answer: yes; at '
                "concurrency 8 a 70-run experiment took 182 to 459 seconds in calibration, and the "
                "baseline itself 266 to 285 seconds, inside the poll and the break.",
                "Transition: Welcome back. The poll asked how much autonomy to grant; now "
                "we earn it.",
            ],
            "container": "fixed template slide",
        }
    ],
}
