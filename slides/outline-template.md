# <COURSE>: deck outline

<!-- guide: Fill this in before you build any slide. One row per slide. A slide with no row
here does not go in the deck. Times are clock times from the class start (0:00); the last end
time is the class length. Every "Source" points at the repo or a registered source. -->

Class length: <minutes> min. Sections: <N>. Slides: <count>.

## Opening

| # | Slide | Layout | Time (start-end) | Says in one line | Source in the repo |
|---|---|---|---|---|---|
| 1 | <COURSE TITLE> | title | 0:00-<end> | <what is built, how it is measured> | README.md |
| 2 | Instructor | blank | | | |
| 3 | How the class runs | concept | | | |
| 4 | Setup checks | demo | | <what must work before the first demo> | setup/README.md |
| 5 | Recap | concept | | <the idea from the previous module this class builds on> | |
| 6 | Problem statement: what are we building? | concept | | | |
| 7 | Why this matters | concept | | <cost of the failure, cost of the fix> | |
| 8 | How we will measure | diagram | | <same task, two arms, one referee> | docs/<measurement page> |
| 9 | Glossary | table | | <one line per term> | docs/glossary.md |

## Section <N>: <SECTION NAME>

<!-- guide: Copy this block once per section. -->

The failure this section fixes: <one sentence>.
The demo: `<command>`, launched at <time>, walked at <time>, fallback in `<section>/demo/expected/`.

| # | Slide | Layout | Time | Says in one line | Source in the repo |
|---|---|---|---|---|---|
| | Agenda (section <N> highlighted) | concept | | | |
| | Failure story: <title> | diagram | | <illustrative ticket, three to five beats> | <section>/concepts.md |
| | <Piece>: <the tempting question>? | concept | | <the verdict, as the KEY IDEA> | |
| | 1) <concept> | concept | | <key idea> | <file> |
| | 2) <concept> | concept | | <key idea> | <file> |
| | 3) <concept> | concept | | <key idea> | <file> |
| | 4) <concept> | concept | | <key idea> | <file> |
| | Cheat sheet: <the piece in four moves> | table | | | |
| | Section <N>: <name> - Implementation Notes: <demo title> | demo | | <screens to walk, in order> | <section>/demo/walkthrough.md |
| | Questions | concept | | <two likely questions> | |
| | Break or poll | blank | | | |

Numbers this section states (each gets a "Re-check after live runs" line in its notes):

- <number>: from `docs/evidence/<file>.md`

## Closing

| # | Slide | Layout | Time | Says in one line | Source in the repo |
|---|---|---|---|---|---|
| | Final demo: reading it live | demo | | | final-project/ |
| | All results: one picture | table | | <one row per section> | docs/evidence/ |
| | Which piece when | table | | <match the piece to the failure> | |
| | Use it in your repo | concept | | <the command that copies the kit> | use-in-your-repo/ |
| | Final project | concept | | | final-project/README.md |
| | Summary: key takeaways | concept | | <the one rule of the class> | |
| | References | table | | <every source, in order of first use> | docs/references.md |
| | Questions and close | concept | | | |

## Checks before building slides

- [ ] Every number has a source file in the repo.
- [ ] Every section has exactly one demo slide, and its command exists in the repo.
- [ ] The times add up to the class length, breaks included.
- [ ] Names are plain; codes appear only in brackets.
- [ ] No people's names, run ids, or dates.
