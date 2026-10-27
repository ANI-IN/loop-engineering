"""Opening block, 0:00-0:13: 13 slides under design system 3 (slides/design-system.md, "The third
rebuild").

The title (the one place in the deck that spells out Structured Query Language), the instructor
and the seven logistics slides copied from the previous module's deck and adapted only where this
module differs or the course's style requires it, the two-slide recap of the previous module
(harness engineering made one run trustworthy; Loop Engineering makes the system trustworthy over
time), and Today's Agenda with the four loops and no star. The copied slides hold their visible
text as lines in the order the deck builder fills the reference slide's text slots (`COPIED` in
slides/source/build.py). Logistics facts come from docs/costs.md ("The learner key limit",
"LangSmith traces") and sources 119 and 120; the four loops from source 1.
"""

RULES = "design system 3"


def short(purpose: str, say: str, transition: str, *do: str) -> list[str]:
    """The short notes form: Purpose, What to say, any Do lines, Transition."""
    return [
        f"Purpose: {purpose}",
        f"What to say: {say}",
        *(f"Do: {x}" for x in do),
        f"Transition: {transition}",
    ]


SLIDES = [
    # 1 title -------------------------------------------------------------------------------------
    dict(
        kind="title",
        title="Loop Engineering for Data Agents",
        minutes=1,
        says="The course title, the subtitle in the reference's style, and what the agent does",
        src="the owner's specification of 27 October 2026, section 2, item 1",
        on_slide=[
            "Loop Engineering for Data Agents",
            "Agent, verification, events, improvement: build each loop, then measure it",
            "One agent that writes Structured Query Language (SQL)",
        ],
        notes=short(
            "Open the class and name what learners leave able to do: build and measure the four "
            "loops around a data agent.",
            "Welcome to Loop Engineering for Data Agents. Today we take one agent that turns plain "
            "business questions into Structured Query Language, SQL, and build the four loops "
            "around it: the agent loop, the verification loop, the event loop and the "
            "hill-climbing loop. We build each loop, then we measure it, and every demo runs live "
            "on the real model.",
            "First, who is teaching today.",
        ),
    ),
    # 2 introduction (copied, reference slide 2) ----------------------------------------------------
    dict(
        kind="intro",
        title="Introduction",
        minutes=0.5,
        says="The instructor introduces themselves",
        src="the reference deck, slide 2, copied as it is",
        on_slide=["**Introduction -** {Instructor_Details}"],
        notes=short(
            "Introduce the instructor in under a minute.",
            "Introduce yourself in two sentences: what you build, and one loop that saved you, or "
            "cost you, in production.",
            "Before we begin, tell us about yourself in the chat.",
            "Replace {Instructor_Details} with your name and title before class.",
            "Before class, check that the Improve page shows Run the naive analyzer (planted); it "
            "appears only while demo controls are on, and the approval demo and the naive "
            "analyzer need them.",
        ),
    ),
    # 3 instructor profile (copied, reference slide 3) ----------------------------------------------
    dict(
        kind="profile",
        title="Welcome to today's class",
        minutes=0.5,
        says="Learners post their name, role, location and organization in the chat",
        src="the reference deck, slide 3; its instructor's details replaced by placeholders",
        on_slide=[
            "Welcome to today’s class, before we begin,",
            "pop into the chat:",
            "{Instructor_Name}",
            "{Instructor_Role}",
            "{Instructor_Location}",
            "{Instructor_Company}",
        ],
        notes=short(
            "Get every learner talking in the chat in the first minutes.",
            "Welcome, everyone! Before we begin, pop into the chat and tell us four things about "
            "yourself: your name, your role, your location and your organization. I will go "
            "first, with the four on the slide.",
            "Here is how the class runs.",
            "Fill in the four placeholders with your own details before class.",
        ),
    ),
    # 4 structure of class (copied, reference slide 4) ----------------------------------------------
    dict(
        kind="logistics",
        variant="structure",
        title="Structure of Class",
        minutes=1,
        says="The live class on Sunday, then the coding assignments",
        src="the reference deck, slide 4; the course's four assignments and Thursday review",
        on_slide=[
            "Structure of Class",
            "Sunday Class - 4 hours (Sunday)",
            "**Assignments -** Coding assignments, reviewed on Thursday",
        ],
        notes=short(
            "Set the shape of the class: the live session, then the coding assignments.",
            "This class has the same structure as every class in the program: a four-hour live "
            "class on Sunday, then coding assignments, one for each loop, reviewed in the Thursday "
            "session. Pace yourself: four hours is long, and the breaks are there for a reason. "
            "The class is recorded, in case you miss a part or want to review it.",
            "How to get the most out of it.",
        ),
    ),
    # 5 optimize your experience (copied, reference slide 5) ----------------------------------------
    dict(
        kind="logistics",
        variant="optimise",
        title="Optimize Your Experience",
        minutes=0.5,
        says="Interact, ask, do the assignments, use the resources",
        src="the reference deck, slide 5",
        on_slide=[
            "Optimize Your Experience",
            "Interact with your instructors via Sunday live class.",
            "Don’t be shy to speak up and get clarifications!",
            "Solve your assignments and other assessments and get feedback (Thursday review "
            "session)",
            "Use your resources! It’s your experience – what you put in is what you’ll get out.",
        ],
        notes=short(
            "Ask learners to take part, to ask, and to use the review session.",
            "Interact with us in the live class, and speak up when something is unclear. Solve "
            "the assignments and bring them to the Thursday review session for feedback. What you "
            "put in is what you get out.",
            "And you are not on your own.",
        ),
    ),
    # 6 support team (copied, reference slide 6) ----------------------------------------------------
    dict(
        kind="logistics",
        variant="support_team",
        title="Don't worry! We are here to help",
        minutes=0.5,
        says="The support team is there at every step",
        src="the reference deck, slide 6",
        on_slide=["Don’t worry!", "We are here to help at your every step!", "But, how???"],
        notes=short(
            "Reassure learners that help is there at every step.",
            "Don't worry: we are here to help at every step of the course, in class and after it. "
            "So how, exactly? Here is how.",
            "The support features.",
        ),
    ),
    # 7 support features (copied, reference slide 7) ------------------------------------------------
    dict(
        kind="logistics",
        variant="support_features",
        title="Support features",
        minutes=0.5,
        says="Uplevel, post-class videos, coaching, Discord, teaching assistants, support tickets",
        src="the reference deck, slide 7; the program's support features, kept as the reference "
        "states them",
        on_slide=[
            "Are you using all these support features?",
            "**Uplevel** - contains all the learning resources - videos, assignments",
            "Optional **Post-class videos** for additional reference",
            "**Technical coaching sessions** on Wednesday to clarify all your queries",
            "**Discord** community for peer learning",
            "**Teaching assistants** to help answer the queries in the live class",
            "**Support tickets** - Raise them any time you want clarifications or technical help "
            "on Uplevel",
        ],
        notes=short(
            "Name every support channel once, so learners know where each kind of question goes.",
            "Uplevel holds every learning resource. The coaching sessions on Wednesday answer "
            "your technical questions, Discord is for learning from each other, the teaching "
            "assistants answer in the chat today, and a support ticket on Uplevel reaches us any "
            "time.",
            "Some habits that help.",
        ),
    ),
    # 8 success hacks (copied, reference slide 8) ---------------------------------------------------
    dict(
        kind="logistics",
        variant="success",
        title="Success Hacks",
        minutes=0.5,
        says="Habits that help learners finish",
        src="the reference deck, slide 8, and its notes",
        on_slide=[
            "Success Hacks",
            "Be prepared for the class by watching the pre-class videos",
            "Attend every class",
            "Participate in class",
            "Attempt all the assignments",
            "Actively advocate for yourself",
            "Keep your goal in mind",
            "Consistency is the key",
            "Be patient with yourself!",
        ],
        notes=short(
            "Share the habits that help learners finish the course.",
            "Please note: the pre-class videos are required, and watching them before class makes "
            "today easier to follow. The post-class videos are optional, and nothing later "
            "depends on them. Above all, be consistent, and be patient with yourself.",
            "Now the two keys you need today.",
        ),
    ),
    # 9 the OpenAI key (copied, reference slide 9) --------------------------------------------------
    dict(
        kind="logistics",
        variant="api_key",
        title="Check Your Email for Your OpenAI Key",
        minutes=1,
        says="The OpenAI key from operations, its 3-dollar limit, and where to ask",
        src="the reference deck, slide 9; docs/costs.md, The learner key limit; sources.py "
        "entry 120",
        on_slide=[
            "Check Your Email for Your OpenAI Key",
            "Operations emailed you an OpenAI application programming interface (API) key with a "
            "3-dollar limit.",
            "If you do not see this email:",
            "Please check your inbox",
            "Also check your spam or junk folder",
            # the deck fills the address from the copied reference slide; it is never published
            "If you still cannot find it, please reach out to the Operations Team "
            "{operations_email}",
            "{API_Key_Email_Screenshot}",
        ],
        notes=short(
            "Make sure every learner has the OpenAI key the demos and assignments use.",
            "The Operations Team emailed each of you an OpenAI key with a spending limit of 3 "
            "dollars. Running every assignment check five times costs about 1.16 dollars, so the "
            "limit leaves room. Only a hard spend limit makes calls fail once it is reached, and "
            "spend can run slightly past it, Source [^120]. If the email is not in your inbox or "
            "your spam folder, write to operations at the address on the slide.",
            "And the tracing key.",
            "Replace the placeholder card with a screenshot of the real email, its key hidden, "
            "once operations sends it.",
        ),
    ),
    # 10 LangSmith (copied, reference slide 10) -----------------------------------------------------
    dict(
        kind="logistics",
        variant="langsmith",
        title="LangSmith Setup Guide",
        minutes=1,
        says="The steps to a LangSmith key, and the free plan's trace limit",
        src="the reference deck, slide 10; docs/costs.md, LangSmith traces; sources.py entry 119",
        on_slide=[
            "LangSmith Setup Guide",
            "Steps to Generate a LangSmith API Key",
            "Note: Free Developer plan, no payment method on file: 5,000 traces a month[^119]",
        ],
        notes=short(
            "Make sure every learner can open the traces of their own runs.",
            "Every run you make today and in the assignments sends a trace to LangSmith, so you "
            "can open each model call and tool call. The free Developer plan, with no payment "
            "method on file, includes 5,000 traces a month, Source [^119]; past that, uploads are "
            "refused until the month resets. The course "
            "traces a sample of its benchmark runs, so one learner's whole course fits about "
            "three times over. Follow the guide behind the button to create your key.",
            "Before the problem, a two-slide recap of the previous module.",
        ),
    ),
    # 11 recap: harness engineering -----------------------------------------------------------------
    dict(
        kind="concept",
        title="Recap: Harness engineering made one run trustworthy",
        minutes=2.5,
        says="The previous module: four layers around one agent run, from start to done",
        src="the reference deck, slides 1, 13 and 14 (its subtitle, its agenda's four layers)",
        figure={
            "diagram": "recap-harness",
            "alt": "Harness engineering, the previous module: one agent run, the same model calling its "
            "tools, with four layers around it, each with an arrow into the run: instructions, "
            "what it knows; state, what it remembers; scope, what it may change; and "
            "verification, what proves it is done",
        },
        on_slide=[
            "Lead: Last module: four layers around one agent run, from its start to done.",
            "Key idea: A harness makes one run trustworthy: what it knows, keeps, may change, "
            "and proves.",
        ],
        notes=[
            "Purpose: Recall the previous module's four layers, so learners see what one "
            "trustworthy run needs before we ask what many runs need.",
            "What to say: Let's start from where the last module ended. Harness engineering was "
            "about one agent run: one task, from its start to done. Look at the middle of the "
            "diagram. The same model calls its tools in a loop, and nothing about the model "
            "changes. What changed was the harness, the four layers around the run, each with an "
            "arrow into it. Top left, instructions: what the agent knows, given as a map it can "
            "follow, not a manual it must memorise. Top right, state: what it remembers between "
            "steps and between sessions, so a long task does not start again from nothing. Bottom "
            "left, scope: what it may change, so a run that goes wrong stays inside its sandbox. "
            "Bottom right, verification: what proves the task is done, a check outside the model "
            "rather than the model's own word. With those four layers, one run of a coding agent "
            "became something you could trust: it knew the rules, kept its place, stayed in "
            "bounds, and proved its result. Hold on to that picture, one run inside a boundary, "
            "because the next slide keeps the same shape and changes what sits in the middle.",
            "The point to land: Harness engineering made one run trustworthy by adding four "
            "layers of code around the same model.",
            "Example: In the last module a coding agent worked tickets on TeamTrack, a small "
            "multi-tenant issue tracker; its first failure story was a search that showed another "
            "organization's issues.",
            'Ask the room: "Which of the four layers did you add to your own agent after the last '
            'module?" Expect: instructions and verification most often; scope least.',
            "Misconceptions: That the harness made the model smarter. The model was the same in "
            "every run; the harness changed what it knew, kept, touched and had to prove.",
            "Transition: One trustworthy run is not a trustworthy system. Here is what changes "
            "when the runs never stop.",
        ],
    ),
    # 12 recap: Loop Engineering --------------------------------------------------------------------
    dict(
        kind="concept",
        title="Recap: Loop Engineering makes the system trustworthy",
        minutes=2.5,
        says="This module: many runs, events and changes over time, and the four loops around them",
        src="sources.py entry 1; the owner's specification of 27 October 2026, section 2, item 3",
        figure={
            "diagram": "recap-loops",
            "alt": "Loop Engineering: the system over time, many runs, events that arrive at any hour, "
            "and rules that change, with the same model in every run; around it the four loops, "
            "each with an arrow into the system: the agent loop, what the agent sees; the "
            "verification loop, what checks the answer; the event loop, what runs unattended; and"
            " the hill-climbing loop, measured improvement",
        },
        on_slide=[
            "Lead: From one run to the system: many runs, events at any hour, rules that change.",
            "Key idea: Four loops make the system trustworthy across many runs, events and "
            "changes.",
        ],
        notes=[
            "Purpose: Frame this module: trust across many runs, events and changes over time, "
            "earned by four loops around the same model.",
            "What to say: Same shape as the last slide, on purpose. The boundary no longer holds "
            "one run; it holds the system, over time. Inside it, many runs, a stack of them, "
            "because a data agent answers questions all day. Events arrive at any hour, from a "
            "chat tool or a schedule, and start runs with nobody watching. And the rules change: "
            "the business rules the answers depend on are learned and revised. At the bottom, the "
            "same model in every run: we never change the model today. Around the system, four "
            "loops, each in its colour. The agent loop, blue: what the agent sees, through tools "
            "that show the right view, capped. The verification loop, teal: what checks the "
            "answer before anyone reads it. The event loop, orange: what lets the system run "
            "unattended, when events repeat, workers restart and someone presses stop. The "
            "hill-climbing loop, lime: what improves the system, measured on questions the "
            "rule writers never saw. The four names come from LangChain's article on loop "
            "engineering, Source [^1], which says the first three loops automate work and the "
            "fourth, arguably the most important, automates improvement. Each of today's sections "
            "builds one of these loops, then measures it.",
            "The point to land: A harness made one run trustworthy; the four loops make the whole "
            "system trustworthy across many runs, events and changes.",
            "Example: One question runs through the whole class, net revenue in fiscal year "
            "2025, and each section shows what its loop does to that answer.",
            'Ask the room: "Which of these loops has failed you in production?" Expect: the '
            "verification loop, a wrong answer nobody checked, and the event loop, a duplicate "
            "message.",
            "Misconceptions: That a better model removes the need for loops. Each loop is code "
            "around the model; a stronger model still repeats events and misses unwritten rules.",
            "Transition: Here is the plan for today, one loop at a time.",
        ],
    ),
    # 13 today's agenda: the four loops, no star -----------------------------------------------------
    dict(
        kind="agenda",
        title="Today's Agenda",
        minutes=1,
        says="The four loops in order, one per section, no star",
        src="the owner's specification of 27 October 2026, section 2, item 4",
        on_slide=[
            "1. Agent loop: what it sees",
            "2. Verification loop: is it right?",
            "3. Event loop: runs unattended",
            "4. Hill-climbing loop: improves safely",
        ],
        notes=[
            "Purpose: Show the plan of the day and what learners will be able to do by its end: "
            "four sections, one loop each.",
            "What to say: Before Section 1, about half an hour on the problem and on how a "
            "text-to-SQL system is designed. Then four sections, one loop each. By 4:00 you will "
            "be able to design what an agent sees, check its answers in code and in the "
            "database, run it safely from events, and improve it on questions it never saw. "
            "First the agent loop, what it sees; then the verification loop, whether the answer "
            "is right. After the first break, the event loop, running unattended; after the "
            "second, the hill-climbing loop, improving safely. Every later loop checks, runs or "
            "improves what the agent loop produces, and each section ends with a live demo and a "
            "measurement with and without its loop.",
            "The point to land: Four loops, one per section, each built and then measured.",
            "Example: The fiscal year 2025 revenue question comes back in every section.",
            "Ask the room: none here; the first question to the room comes with the problem.",
            "Misconceptions: That the loops are layers of one prompt. Each is code around the "
            "model.",
            "Transition: First, the problem: what we are building, and what goes wrong without "
            "the loops.",
        ],
    ),
]
