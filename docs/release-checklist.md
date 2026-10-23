# Release checklist

The checks that must pass before the course repository is published, in order. Each row names the
command or the person that confirms it. Tick a row only after you have seen it pass.
<!-- provisional: the make targets named here are built by the platform tracks; the page is a draft until the rehearsal milestone -->

## Before the final rehearsal

| Check | How you confirm it | Done |
|---|---|---|
| Every page passes the strict style check | `make check-style-strict` reports 0 errors and 0 warnings | No |
| The prose lint is clean | `uv run python platform/scripts/lint_prose.py` reports 0 problems | No |
| Generated pages are current | `make docs-check` reports 0 out of date | No |
| The naming rule holds in commit messages | `make check-short-forms` reports 0 found | No |
| The preflight canary passes on the class model | `make preflight PURPOSE=rehearsal` | No |
| Calibration is recorded with its date and returned model id | `docs/calibration-report.md` | No |
| Every activity stays inside its budget line | `make spend` shows each line | No |
| The reserve is unused without written approval | `make spend` shows the reserve line | No |
| Total spend stays under 10 dollars, with the final rehearsal still covered | `make spend` | No |

## The final rehearsal

| Check | How you confirm it | Done |
|---|---|---|
| The final rehearsal runs in its own live session | `make preflight PURPOSE=rehearsal`; the status line shows its start | No |
| Every core demo passes live twice in a row, with a reset between | The rehearsal log | No |
| Fresh runs: every demo produced new run ids during that rehearsal itself | Run ids and start times in the log fall inside the rehearsal session | No |
| The class and the Thursday review each start their own session | `PURPOSE=class` and `PURPOSE=thursday-review` in their run sheets | No |
| Every result on the console shows its live stamp and trace link | Point at each stamp during the rehearsal | No |
| The baseline experiment is accepted only from the open session | The console refuses an earlier baseline | No |
| No demo opens a `demo/expected/` folder | The run sheet and the rehearsal log | No |
| Recovery is reset and run it again in every runbook and note | Read the instructor guide and the DEMO notes | No |
| DEMO slides hold only the badge and the title | `slides/scripts/extract_deck.py` on the deck | No |
| No font falls back on the presenting machine | On that machine, Replace Fonts lists only Fira Sans; the DEMO badge is a shape | No |
| One timed dry run of the Thursday review fits 120 minutes | [The review session](review-session.md) | No |

## Publishing

| Check | How you confirm it | Done |
|---|---|---|
| The solutions stay unpublished until the Thursday review | The `solution/` folders are absent from the published tree | No |
| The solutions are published at the start of the Thursday review | The first step of [the review session](review-session.md) | No |
| The published tree holds only the allow-listed files | `platform/config/release.toml` and the release build output | No |
| No secrets or `.env` file in the published tree | The secret scan reports nothing | No |
| Nothing is pushed until the course owner confirms name and visibility | Written confirmation | No |
