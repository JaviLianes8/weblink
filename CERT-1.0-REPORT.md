# weblinking 1.0.0 certification report

The 1.0.0 certification bar applied to weblinking. Nothing of this project is on PyPI:
the name it was developed under was refused at upload as too similar to an existing
project, so the distribution and the import package are now `weblinking` (the title of
RFC 8288, "Web Linking"). There is no earlier release to upgrade from.

Progress:
- [x] Branch `release/1.0.0` created from `main` (123a468, version 0.2.0, never published)
- [x] Baseline gates on 0.2.0
- [x] New name chosen and applied to the distribution, the package and the command
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Ground truth: sources fetched live, reference implementations (item 7)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e, every Python (items 8, 10, 13, 14)
- [x] Gates (item 15)
- [x] Pull request and trace guard
- [ ] Five QA lenses report PASS (item 19)
- [ ] Independent reviewer reports PASS (item 16)

## Scorecard (author's run; items 16, 17 and 19 belong to other agents)

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: names, signatures, parameter names and defaults pinned by `tests/test_contract_api.py`; every change in the CHANGELOG |
| 2 | `__all__` exact, no private imports in docs | PASS: `tests/test_contract.py` |
| 3 | Docstrings with runnable examples | PASS: every public name and every `Link` member; doctests run with their own module globals, plus README and GUIDE examples |
| 4 | Typed end to end | PASS: `mypy --strict src tests`, `py.typed` shipped, typing checked from a consumer |
| 5 | Typed, documented, bounded errors | PASS: `LinkError` (a `ValueError`) with `message` and `position`, `TypeError` for wrong types, messages quote at most 80 characters |
| 6 | Contract tests of every public name | PASS |
| 7 | Real ground truth | PASS: see Ground truth |
| 8 | Real e2e from the wheel, CLI by subprocess | PASS: no PyPI release exists, so no upgrade path |
| 9 | Seeded fuzz, no crash, hang or blowup | PASS |
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.14, 3.12.12, 3.13.11, 3.14.2, 3.14.2t, 3.14.6 |
| 11 | README, `twine check --strict` | PASS |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-19 |
| 13 | pyproject 1.0.0, Production/Stable | PASS |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates |
| 18 | Contracts bite (mutations) | PASS: 20 author mutants, 18 killed first time, 1 equivalent (code removed), 1 survivor killed by a new contract |

## Baseline on 0.2.0 (before any change)

At 123a468 on this PC, CPython 3.13.2: `ruff format --check .`, `ruff check .` and
`mypy --strict src tests` exit 0; `pytest` 198 passed, 1 skipped (the installed-wheel
test, which needs its opt-in variable). The six reference files were fetched again on
2026-10-19 with `scripts/fetch_upstream.py`: the four RFCs and the GitHub page match the
manifest byte for byte; the IANA registry file had changed (only its reference column
was reformatted, from `[RFC6903], section 2` to `[RFC 6903, Section 2]`; the 235
relation names are the same), so its manifest entry was updated.

## Name

`weblink` was refused by PyPI at upload. `weblinking` was checked on 2026-10-19 (and
again before the pull request): `https://pypi.org/pypi/<name>/json` answers 404 for
`weblinking`, for every spelling with `-`, `_` or `.` inserted between two letters, and for
the 27 spellings that swap `l`, `i` and `1`; the name has no `o`. The old name stays only
in one CHANGELOG line.

## API review (item 1)

Kept: the names of 0.2.0 with their parameter names and defaults. Changed, all listed in
the CHANGELOG: `TypeError` for arguments of the wrong type everywhere (they used to fail
with `AttributeError` or a bare `ValueError`); `Link` takes a mapping or `(name, value)`
pairs and refuses a string, bytes or items of another length; values are stored as plain
`str`; `Link.context` checks the base also without an `anchor`; `resolve_uri` reads text
before a colon that is not a scheme as a relative path; messages quote at most 80
characters; public classes report `weblinking` as their module.

## Ground truth (item 7)

Fetched on 2026-10-19 by `scripts/fetch_upstream.py` into the ignored `tests/upstream`
folder; `tests/upstream/MANIFEST.json` records URL, revision, size, sha256 and licence.
Nothing fetched is committed or shipped.

- RFC 8288, RFC 8187, RFC 3986 and RFC 9110 from www.rfc-editor.org
  (`tests/test_sources.py`): the section 3.5 examples parse strictly, mean what the RFC
  says and round trip through `build`; the RFC 8187 examples decode and ext-values accept
  exactly its `attr-char`; every RFC 3986 section 5.4 example resolves as listed; names are
  exactly the RFC 9110 tokens and quoted values exactly its `qdtext`.
- IANA Link Relation Types registry (CSV): the shipped names equal the registry, every
  name passes strict parsing in any case, `openid2.local_id` is accepted.
- GitHub REST docs (github/docs commit ee5047f): the pagination headers parse.
- Unicode ISO-8859-1 mapping, https://www.unicode.org/Public/MAPPINGS/ISO8859/8859-1.TXT
  (read 2026-10-19, sha256 2a06a462...bb5e): its 256 entries map each octet to the code
  point of the same number, which the contract added in this round pins.
- Reference parsers run in this session (`tests/test_oracles.py`): httplink 0.2.0,
  ietfparse 1.9.0, requests 2.34.2 and the Node.js `http-link-header` 1.1.4 on 12,000
  generated headers each (three seeds); every difference is a stated rule of the other
  library and is asserted as such.
- Resolution (`tests/test_oracle_uri.py`): RFC 3986 section 5.2 written out step by step
  on 100,000 references per seed, and the `rfc3986` 2.0.0 package, whose four departures
  from the RFC text are named and asserted.
- Real servers (`tests/test_live.py`, `WEBLINKING_LIVE=1`): GitHub pagination followed
  forward and back, GitLab pagination read strictly; passed in the runs below.

## Fuzz and hostile input (item 9)

`tests/test_fuzz.py`: eleven seeds of 3,000 to 20,000 inputs per property (lenient
parsing never raises, strict parsing raises only `LinkError` with a position on the line,
strict and lenient agree on accepted input, `build` output reads back unchanged, ext-values
decode or fail cleanly and round trip, hostile references resolve without crashing, the
command reads hostile `curl -i` heads). `tests/test_hostile.py`: sixteen input shapes timed
at n and 4n characters (linear), many parameters, 1 MB in every error path (messages
under 300 characters).

## Author mutation round (item 18)

Each mutant applied alone to a fresh clone of 9ecf91e (with the test change of 91aaf07) on the laptop, the full suite run
(fetched sources, the four reference parsers present) with a 300 s per-test limit.

| # | Module | Mutation | Result |
| --- | --- | --- | --- |
| 1 | `_parse` | parameter names no longer lower-cased by the parser | equivalent: `Link` lower-cases names; the redundant call was removed in af52408 |
| 2 | `_parse` | quoted-pair keeps the backslash | killed (13): `test_build_keeps_tabs_and_printable_ascii`, oracles, fuzz |
| 3 | `_parse` | lenient resync stops at `;` instead of `,` | killed: `test_malformed_segments_are_skipped` hangs and hits the timeout |
| 4 | `_parse` | a quoted RFC 8187 value accepted in strict mode | killed: `test_a_star_value_must_not_be_quoted` |
| 5 | `_uri` | merge drops the last `/` of the base (off by one) | killed (16): `test_base_resolves_targets`, README and GUIDE examples |
| 6 | `_uri` | an empty reference loses the base query | killed (5): the RFC pseudocode oracle, `rfc3986` |
| 7 | `_uri` | `..` no longer removes the previous segment | killed (14): CLI, README, GUIDE |
| 8 | `_uri` | a network-path reference takes its own scheme (swapped argument) | killed (6): the RFC pseudocode oracle |
| 9 | `_ext` | percent escapes decoded to 7 bits | killed (16): `test_build_writes_star_values_bare_and_checks_them`, docs |
| 10 | `_ext` | ISO-8859-1 decoded as windows-1252 | survived; killed by `test_iso_8859_1_maps_every_octet_to_the_code_point_of_the_same_number` (af52408) |
| 11 | `_ext` | encoder writes lower-case hex | killed (5): build and docs examples |
| 12 | `_ext` | unknown charset raises `ValueError` instead of `LinkError` | killed (5): `test_decode_rejects_malformed_values` |
| 13 | `_find` | relation types compared with case | killed (2): `test_find_picks_links_by_relation_type`, doctests |
| 14 | `_build` | backslashes no longer escaped | killed (2): `test_build_keeps_tabs_and_printable_ascii`, round trip |
| 15 | `_check` | a repeated `rel`, `title` or `type` accepted once more (off by one) | killed (9): `test_build_refuses_a_parameter_allowed_once_written_twice` |
| 16 | `_check` | a link without `rel` accepted | killed (4): `test_rel_is_required`, build, CLI |
| 17 | `_errors` | messages quote ten times more | killed (18): `test_error_messages_quote_at_most_eighty_characters` |
| 18 | `_model` | `params` keeps the last repeated value | killed (5): `test_names_are_lower_cased_and_pairs_keep_order`, docs |
| 19 | `_model` | `get` returns the raw starred value it cannot decode | killed (2): `test_title_falls_back_when_the_star_form_is_broken` |
| 20 | `_model` | `resolve` leaves `anchor` unresolved | killed (2): `test_resolve_resolves_the_target_and_the_anchor`, RFC 8288 section 3.1 |

## Packaging, e2e and Pythons (items 8, 10, 13, 14)

- `tests/test_e2e_wheel.py` (`WEBLINKING_E2E=1`) builds the wheel and sdist, inspects
  both (no tests, scripts or fetched files in the wheel; LICENSE, GUIDE, the manifest and
  no fetched file in the sdist; 1.0.0 and Production/Stable in the metadata; only the
  `dev` extra requires anything), installs the wheel in a fresh venv, runs a consumer
  program from an empty folder with `-I`, and drives `weblinking` and
  `python -m weblinking` by subprocess, including exit status 2 on an error.
- Interpreter matrix at af52408 on the laptop: fresh clone, wheel and sdist built,
  `twine check --strict` PASSED for both, contents listed (wheel: the package, `py.typed`,
  metadata and `licenses/LICENSE`; sdist: sources, tests, scripts, docs, LICENSE and the
  manifest, no fetched files, no report files). For each interpreter a fresh venv with the
  wheel installed and the sdist's own suite run with `src` removed and the fetched files
  and reference parsers present: CPython 3.10.19, 3.11.14, 3.12.12, 3.13.11, 3.14.2 and
  3.14.2 free-threaded, 317 passed and 3 skipped each (the e2e and the two live tests,
  opt-in, run in the gates below). 3.8 and 3.9 are below `requires-python`.

## Gates (item 15)

At 79f9c27 on the laptop from a fresh clone, CPython 3.14.6, each command on its own,
with the fetched sources, the reference parsers, `WEBLINKING_E2E=1` and
`WEBLINKING_LIVE=1`: `ruff format --check .`, `ruff check .`, `mypy --strict src`,
`mypy --strict src tests` and `pytest` (320 passed, no skips) all exit 0.

## QA lenses (item 19)

### Round 1 (on 34db338)

Five lenses: a (API and docs), b (correctness and ground truth), c (adversarial),
d (packaging and e2e), e (contract strength, own mutation round). Every finding was
fixed; none is disputed. Behaviour fixes got a contract in `tests/test_qa_fixes.py`
that failed on 34db338 first (run against an export of that commit), then passed.

| Lens | Finding | What changed |
| --- | --- | --- |
| a F1, b F3, d D1 | Project URLs and README links named a repository that does not exist | Every link points at github.com/JaviLianes8/weblink (pyproject URLs, README, the `test_docs` pin, the `test_cli` fixture comment). The repository, its issues, `CHANGELOG.md` and `LICENSE` on `main` answer 200; `GUIDE.md` and this report answer 200 on `release/1.0.0` and reach `main` with the merge |
| a F2 | README and GUIDE named parameters that do not exist | The API table and the GUIDE give the real names and defaults: `relation_type`, `encode_ext_value(value, language="")`, `Link(uri, params=())` |
| a F3 | The `params` type refused the list pairs the docs promise | `Params` accepts `list[str]` pairs; `tests/test_typing.py` type-checks a literal list pair and a `json.loads` result |
| a F4 | `find` and `find_all` examples relied on injected globals | The examples import what they use; the doctest test runs each module with its own globals, so `pytest --doctest-modules src` and `doctest.testmod` pass too |
| a F5 | The prescribed dev setup failed `mypy --strict src tests` | The `dev` extra installs `rfc3986==2.0.0`, `httplink==0.2.0`, `ietfparse==1.9.0` and `requests==2.34.2`, the versions the tests pin; checked in a fresh venv from `requirements-dev.txt` (gates below) |
| a F6 | `del` on a `Link` attribute succeeded | `__delattr__` raises `AttributeError("Link is immutable")`: `test_attributes_cannot_be_deleted_or_assigned` |
| a F7, c F4 | Parameter names folded with Unicode `lower()` (Kelvin sign to `k`) | Names fold only ASCII letters in `Link`, `get` and `get_all`, so such a name stays a non-token that `build` refuses: `test_parameter_names_fold_only_ascii_letters` |
| a F8 | CHANGELOG history was inaccurate | 0.2.0 and 0.1.0 are dated and marked as unpublished development versions named `weblink`; the 0.2.0 command is `weblink` |
| a F9 | Eleven `Link` members had no example | Every `Link` member has one (the accessors moved to the private `_access` module to keep files under 200 lines); `test_every_link_member_has_an_example` checks all 17 |
| b F1 | `rels` split on any Unicode whitespace | `rels` splits on runs of SP, HTAB, CR and LF only: `test_relation_types_split_only_on_spaces_and_tabs` (NBSP, NEL, VT, FF, U+001C, U+2003, U+3000) |
| b F2 | Strict ext-value checking was described as the RFC 8187 grammar | Documentation fix: `parse`, `build`, `decode_ext_value`, the GUIDE and the README state the rule applied (UTF-8 and ISO-8859-1 only, escaped octets must decode, a light language check, not RFC 5646) |
| c F1 | Error messages quoted credentials and signed queries | Messages about a target, an anchor or a base URI show its userinfo and query as `***`: `test_error_messages_never_quote_credentials_or_queries`, `test_redacted_messages_keep_the_rest_of_the_value` |
| c F2 | `parse` ran the methods of a `str` subclass | Each line is read as a plain `str`: `test_parse_reads_str_subclasses_as_plain_text` (it hung on 34db338) |
| c F3, d D2 | A closed stdout pipe printed a traceback | The command stops quietly with status 1 (EPIPE, or EINVAL on Windows) and points stdout at the null device: `test_the_command_exits_quietly_when_the_reader_stops_early` by subprocess |
| e F1-P02 | Survivor: name no longer stops at a comma | `test_a_valueless_parameter_ends_at_a_comma` |
| e F2-P13 | Survivor: unclosed quote ending in a backslash | `test_strict_refuses_an_unclosed_quote_ending_in_a_backslash` |
| e F3-L02 | Survivor: equality by set of pairs | `test_equality_and_hash_follow_pair_order_and_repetition` |
| e F4-L13 | Survivor: last anchor used | `test_the_first_anchor_is_the_context` |
| e F5-L14 | Survivor: `rel` read through `get` | `test_a_starred_rel_never_overrides_rel` |
| e F6-L11 | Survivor: `__setattr__` dropped | `test_attributes_cannot_be_deleted_or_assigned` |

The six lens e mutants were applied again, one at a time, to the fixed tree: each is
killed by the test named above.

Fix commit c8eb48a. Gates on this PC from a fresh clone of that commit, a new venv with
`pip install -r requirements-dev.txt` (CPython 3.13.2), the fetched sources and
`http-link-header` 1.1.4, `WEBLINKING_E2E=1` and `WEBLINKING_LIVE=1`:
`ruff format --check .`, `ruff check .`, `mypy --strict src`, `mypy --strict src tests`
and `pytest` (347 passed, no skips) all exit 0.

Disputed findings: none.
