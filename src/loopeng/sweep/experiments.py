"""The arm summaries the three headline charts draw from.

**Nothing supplied them until now, and that is the finding this module exists for.**

`write_charts` has always accepted `arms` and `trap_cells`. `outcome_shift_chart`,
`trap_matrix_chart` and `cost_per_correct_chart` have always been written, tested and
captioned. And the only caller — `demos/04_hill_climbing_loop/charts.py` — passed
neither, so all three rendered *not yet measured* on every run this project has ever
done, including the one whose headline they are.

That is the same shape as prompt caching and the discarded failure taxonomy: the
instrument was built, the data existed on disk in `results/experiments/`, and no line
connected them. Here it landed on the session's primary visual.

WHY THE TRAP MATRIX IS ASSEMBLED RATHER THAN READ

The trap is four cells — two models by two prompt levels — and no single file holds
them. `trap-agent-L0` and `trap-reference-L0` are the withheld arms; the rules-given
arms are conditions A and D, which exist for a different comparison. The matrix is that
join, and it is written down here rather than in a chart caller so the two levels cannot
be paired with the wrong arms.
"""

import json
from pathlib import Path

from loopeng.registry import spec_for

EXPERIMENTS_DIR = Path("results/experiments")

# The order the outcome-shift chart draws, which is the escalation the session walks.
ARM_ORDER = ("trap-agent-L0", "A-baseline", "B-retry", "C-verified", "D-reference")

# (role, level) -> the arm that measured it. The join the trap matrix needs.
#
# A and D are the rules-GIVEN cells, and they are the same runs conditions A and D
# report — one measurement, two comparisons, rather than paying twice and then having
# to explain why the two numbers differ.
TRAP_ARMS = {
    ("agent", "L0"): "trap-agent-L0",
    ("agent", "L3"): "A-baseline",
    ("reference", "L0"): "trap-reference-L0",
    ("reference", "L3"): "D-reference",
}


class MissingArm(LookupError):
    """A named arm is not on disk. Raised rather than drawn as an empty panel.

    An absent arm and an arm that measured nothing look identical once a chart has
    rendered, and only one of them is a result. `scripts/run_experiments.py` writes all
    six or none.
    """


def load_arms(directory: Path = EXPERIMENTS_DIR) -> dict[str, dict]:
    """Every arm summary on disk, by arm name."""
    directory = Path(directory)
    if not directory.is_dir():
        return {}
    arms = {}
    for path in sorted(directory.glob("*.json")):
        if path.name == "summary.json":
            continue
        body = json.loads(path.read_text(encoding="utf-8"))
        if "arm" in body:
            arms[body["arm"]] = body
    return arms


def outcome_shift_arms(arms: dict[str, dict]) -> list[dict]:
    """The arms the outcome-shift chart draws, in the order it draws them.

    Arms absent from disk are skipped rather than faked; arms present but not named in
    `ARM_ORDER` are skipped too, because the chart's whole point is a comparison across
    a fixed ladder and an extra bar changes what the picture argues.
    """
    return [arms[name] for name in ARM_ORDER if name in arms]


def trap_cells(arms: dict[str, dict]) -> list[dict]:
    """The four cells of the trap matrix, joined from the arms that measured them.

    **The model label is derived from the registry**, not from the arm name. An arm is
    called `trap-agent-L0`; the bar has to say which model that was, and a bar captioned
    with a model the run did not call is a defect this project has already found twice.
    """
    cells = []
    for (role, level), arm_name in sorted(TRAP_ARMS.items()):
        arm = arms.get(arm_name)
        if arm is None:
            raise MissingArm(
                f"the trap matrix needs {arm_name!r} for {role} at {level}, and it is "
                f"not in {EXPERIMENTS_DIR}. Run scripts/run_experiments.py — it writes "
                f"all six arms or none, and a matrix drawn from three of them is a "
                f"different picture with no way to tell."
            )
        bands = arm["bands"]
        cells.append({
            "model": spec_for(role).model_id,
            "level": level,
            "correct": bands["correct"],
            "n": arm["n_items"],
        })
    return cells


def available(arms: dict[str, dict]) -> bool:
    """Whether the trap matrix can be drawn at all. False on a fresh checkout."""
    return all(name in arms for name in TRAP_ARMS.values())
