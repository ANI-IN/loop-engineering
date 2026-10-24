# release: private build repository to public course repository

`make_release.py` is a small reference implementation of the release pattern: you build the
course in a private repository (research notes, graders, hidden test cases, internal scripts),
and learners get a public repository made from an allow-list, as one commit.

## The pattern

1. **Allow-list, not deny-list.** A file is public only when a pattern in `allow` matches it.
   New files stay private until someone adds them on purpose.
2. **Private folders win.** Anything under `private_dirs` or in `private_files` is excluded even
   when an allow pattern matches it.
3. **Git objects only.** Files are read from `--ref`, never from the working tree, so untracked
   and uncommitted files cannot leak.
4. **Excluded-test detector.** A public test whose code names an excluded file (a grader, a
   hidden case) would fail for learners; it is dropped and listed. Docstrings do not count.
5. **Leak check.** No private path in the public list; no key-like text, host path, or `deny`
   word in a public file. The report names the file and the kind, never the text.
6. **One commit, then tags.** A fresh repository, one commit by the configured author, then the
   configured tags (a release tag, checkpoint tags) on that commit.
7. **Verify in the public tree.** The `verify` command runs inside the built tree; a red suite
   fails the release.
8. **Dry run by default.** Without `--build`, the tree is built in a temporary folder and
   deleted. Nothing is ever pushed; the owner pushes by hand after reading the report.

## Use

```bash
uv run python platform/scripts/kit/release/make_release.py --config release.json  # dry run
uv run python platform/scripts/kit/release/make_release.py --config release.json --build /tmp/public
```

The configuration format is in the script's docstring. Grow it for your course as needed: a generated
references page, checkpoint tags rebuilt from the private tags, a contributor check. Keep each
addition a pure function with a test, as the ones here are.
