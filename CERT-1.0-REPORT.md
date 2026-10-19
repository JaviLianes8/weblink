# weblinking 1.0.0 certification report

The 1.0.0 certification bar applied to weblinking. Nothing of this project is on PyPI:
the name it was developed under was refused at upload as too similar to an existing
project, so the distribution and the import package are now `weblinking` (the title of
RFC 8288, "Web Linking"). There is no earlier release to upgrade from.

Progress:
- [x] Branch `release/1.0.0` created from `main` (123a468, version 0.2.0, never published)
- [x] Baseline gates on 0.2.0
- [x] New name chosen and applied to the distribution, the package and the command
- [ ] API review and 1.0.0 changes (item 1)
- [ ] Errors, typing, docstrings and doctests (items 2 to 5)
- [ ] Ground truth: sources fetched live, reference implementations (item 7)
- [ ] Contract, fuzz and author mutation round (items 6, 9, 18)
- [ ] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e, every Python (items 8, 10, 13, 14)
- [ ] Gates (item 15)
- [ ] Pull request and trace guard
- [ ] Five QA lenses report PASS (item 19)
- [ ] Independent reviewer reports PASS (item 16)

## Baseline on 0.2.0 (before any change)

At 123a468 on this PC, CPython 3.13.2: `ruff format --check .`, `ruff check .` and
`mypy --strict src tests` exit 0; `pytest` 198 passed, 1 skipped (the installed-wheel
test, which needs its opt-in variable). The six reference files were fetched again on
2026-10-19 with `scripts/fetch_upstream.py`: the four RFCs and the GitHub page match the
manifest byte for byte; the IANA registry file had changed (only its reference column
was reformatted, from `[RFC6903], section 2` to `[RFC 6903, Section 2]`; the 235
relation names are the same), so its manifest entry was updated.

## Name

`weblink` was refused by PyPI at upload. `weblinking` was checked on 2026-10-19:
`https://pypi.org/pypi/<name>/json` answers 404 for `weblinking`, for every spelling with
`-`, `_` or `.` inserted between two letters, and for the 27 spellings that swap `l`, `i`
and `1`; the name has no `o`. The old name stays only in one CHANGELOG line.
