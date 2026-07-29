"""The numeric-literal rule, and the two ways it was previously vacuous.

It pointed at `app/views.py` after the directory was emptied, so it scanned
nothing and exited 0. And the test written to prevent that planted its violation
by *writing* the file — which created the missing target, proving the AST walker
worked while never checking the target was real.

Both failures are covered below, and the second one is why
`test_every_declared_target_exists_on_disk` does not touch the filesystem.
"""

from pathlib import Path

from tools.lint_no_numbers import REPO_ROOT, TARGETS, find_violations, main, missing_targets, scan

FIXTURES = Path(__file__).parent / "fixtures"


# ---- the walker -------------------------------------------------------------


def test_catches_a_typed_integer_measurement():
    violations = find_violations(FIXTURES / "dirty_view.py")
    assert any("78" in literal for _, literal in violations)


def test_catches_a_typed_float_measurement():
    violations = find_violations(FIXTURES / "dirty_view.py")
    assert any("4.25" in literal for _, literal in violations)


def test_reports_the_line_number():
    violations = find_violations(FIXTURES / "dirty_view.py")
    assert all(lineno > 0 for lineno, _ in violations)


def test_allows_structural_zero_and_one():
    """Indexing and off-by-one arithmetic must stay possible. 0 and 1 cannot encode
    a finding; any other literal can."""
    assert find_violations(FIXTURES / "clean_view.py") == []


def test_booleans_are_not_numbers():
    """True is an int subclass in Python. Flagging it would make the rule
    unusable without teaching anyone anything."""
    assert find_violations(FIXTURES / "clean_view.py") == []


def test_main_returns_nonzero_when_a_violation_is_found():
    assert main([str(FIXTURES / "dirty_view.py")]) == 1


def test_main_returns_zero_when_clean():
    assert main([str(FIXTURES / "clean_view.py")]) == 0


# ---- the layout exemption ---------------------------------------------------


def test_geometry_marked_layout_is_exempt():
    """Widening the rule to the real renderers pulls in SVG coordinates and string
    truncation widths. None can encode a finding."""
    assert find_violations(FIXTURES / "layout_view.py") == []
    assert main([str(FIXTURES / "layout_view.py")]) == 0


def test_exemptions_are_counted_not_silent():
    """An escape hatch whose usage nobody counts is how a rule ends up exempting
    everything it was written to catch."""
    _, n_exempt = scan(FIXTURES / "layout_view.py")
    assert n_exempt > 0


def test_the_marker_must_be_a_comment_not_a_string(tmp_path):
    """`# layout` inside a string literal must not exempt the line, or any file
    mentioning the word disarms itself."""
    planted = tmp_path / "sneaky.py"
    planted.write_text('LABEL = "# layout"\nPASS_RATE = 78\n', encoding="utf-8")
    assert find_violations(planted) != []


def test_removing_the_marker_catches_the_literal_again(tmp_path):
    """The exemption is doing real work, not passing by accident."""
    marked = tmp_path / "marked.py"
    marked.write_text("PAD = 300  # layout: gutter\n", encoding="utf-8")
    assert find_violations(marked) == []

    unmarked = tmp_path / "unmarked.py"
    unmarked.write_text("PAD = 300\n", encoding="utf-8")
    assert find_violations(unmarked) != []


# ---- failure 1: a declared target that does not resolve ---------------------


def test_every_declared_target_exists_on_disk():
    """THE regression test, and it deliberately touches no files.

    The previous version planted a violation by writing the target, which CREATED
    the missing path. It could never have caught `app/views.py` being gone.
    """
    assert missing_targets() == [], (
        f"declared lint targets do not exist: {missing_targets()}. The rule scans "
        f"nothing there and reports success."
    )


def test_a_missing_target_fails_the_build_rather_than_passing(monkeypatch):
    """Proven against the exact path that was vacuous for weeks."""
    import tools.lint_no_numbers as lint

    monkeypatch.setattr(lint, "TARGETS", (REPO_ROOT / "app" / "views.py",))
    assert lint.missing_targets() != []
    assert lint.main([]) == 1


def test_no_target_points_into_the_removed_app_directory():
    """`app/` is gone. A target under it can only ever be vacuous."""
    assert not (REPO_ROOT / "app").exists()
    assert not any("app" in path.parts for path in TARGETS)


def test_scanning_an_absent_file_directly_is_still_benign():
    """find_violations stays usable for ad-hoc checks on arbitrary paths. Only a
    DECLARED target is required to exist."""
    assert find_violations(Path("does/not/exist.py")) == []


# ---- failure 2: targets that catch nothing ----------------------------------


def test_the_targets_are_the_modules_that_render():
    """Pinned so a future move updates this deliberately rather than silently
    disabling the rule.

    The old target set was one missing path plus one thin entry point with no
    literals to catch, so live coverage across the whole rule was zero. These are
    the modules that actually build what a room reads.
    """
    views = REPO_ROOT / "src" / "loopeng" / "views"
    assert set(TARGETS) == {
        REPO_ROOT / "src" / "loopeng" / "sweep" / "charts.py",
        views / "dial.py",
        views / "oversight.py",
        views / "trap.py",
        views / "verify.py",
        views / "agent.py",
        views / "exhibit.py",
        REPO_ROOT / "demos" / "04_hill_climbing_loop" / "charts.py",
    }


def test_the_rule_has_live_coverage_not_just_targets():
    """At least one target must contain literals the rule is actively exempting.

    A target set where nothing is ever inspected is the failure mode that hid for
    weeks: green, and inspecting nothing.
    """
    assert sum(scan(path)[1] for path in TARGETS) > 0


def _plant(target: Path, body: str) -> str:
    original = target.read_text(encoding="utf-8")
    target.write_text(body, encoding="utf-8")
    return original


def test_main_with_no_arguments_checks_the_real_targets():
    assert main([]) == 0


def test_default_targets_are_anchored_to_the_repo_not_the_cwd(tmp_path, monkeypatch):
    """A lint rule that reports success because it was run from the wrong directory
    is worse than no lint rule: it produces a green build that checked nothing."""
    planted = TARGETS[-1]
    original = _plant(planted, "X = 42\n")
    try:
        monkeypatch.chdir(tmp_path)
        assert main([]) == 1
    finally:
        planted.write_text(original, encoding="utf-8")


def test_every_default_target_is_actually_checked():
    """Each target in turn is given a literal, and main() must fail on it."""
    assert TARGETS, "the rule has no targets and cannot catch anything"

    for target in TARGETS:
        original = _plant(target, "MEASURED_RATE = 78\n")
        try:
            assert main([]) == 1, (
                f"{target} is a declared target but planting a literal there passed"
            )
        finally:
            target.write_text(original, encoding="utf-8")

    # With the real files restored the same call is clean, which also asserts every
    # shipped target is free of typed measurements.
    assert main([]) == 0


def test_a_planted_literal_is_not_rescued_by_a_layout_marker_elsewhere():
    """The marker is per line. A `# layout` on line 3 must not exempt line 9."""
    target = TARGETS[0]
    original = _plant(target, "PAD = 300  # layout: gutter\nMEASURED_RATE = 78\n")
    try:
        assert main([]) == 1
    finally:
        target.write_text(original, encoding="utf-8")
