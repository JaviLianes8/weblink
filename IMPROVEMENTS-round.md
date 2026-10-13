# weblink improvement round

Progress:
- [x] Brainstorm ranked improvements (this file)
- [x] Pin the ground truth: RFC 8288, RFC 8187, RFC 3986, RFC 9110, IANA registry, GitHub docs
- [x] Ordered parameter model: repeated `hreflang` and extension attributes kept, frozen `Link`
- [x] Parser on the RFC 8288 grammar: several field lines, unquoted values per Appendix B.3
- [x] Strict mode with `LinkError` offsets: ABNF, duplicates, relation types, star values
- [x] RFC 8187 extended values: decode, encode, `title*` preferred over `title`
- [x] RFC 3986 section 5 resolution: target and anchor against a base, strict algorithm
- [x] Safe builder: header injection guard, tokens, `rel` required, star values unquoted
- [x] Relation types: IANA names, `is_registered`, case rules, `find` and `find_all`
- [x] Command line: read a header or a `curl -i` dump, print JSON
- [x] Contracts: pinned sources, README examples, typing, installed wheel
- [x] Docs and packaging: README, CHANGELOG, metadata, sdist contents
- [ ] Gates: ruff format, ruff check, mypy --strict, pytest
- [ ] Mutation run: removing guarded logic makes the suite fail
- [ ] Independent review findings fixed with regression tests
- [ ] Pull request opened, guard clean

## Starting point

`0.1.0` gives `parse`, `build` and a `Link` with a `params` dict. Compared with the
sources below:

- The dict keeps only the first value of each parameter. RFC 8288 section 3.4.1 says
  several `hreflang` values mean several languages, and section 3.4.2 lets extension
  attributes repeat: both are silently lost, and `build(parse(h))` drops them.
- An unquoted value stops at the first space or double quote, while Appendix B.3 reads
  it up to the next `;` or `,`; anything after the space throws the rest of the link
  away.
- `title*` (RFC 8187) is returned as the raw percent-encoded string; section 3.4.1 says
  applications SHOULD prefer it over `title`. Nothing decodes or encodes ext-values.
- Targets and anchors are never resolved, although section 3.1 and 3.2 say a relative
  reference MUST be resolved per RFC 3986 section 5. `urllib.parse.urljoin` is not a safe
  stand-in: it resolves `http:g` the loose way.
- `rels` does not normalise case, so `rel="Next"` is missed by a lookup for `next`, while
  section 2.1.1 says registered types are compared case-insensitively.
- There is no strict mode, so a caller cannot validate what a server sends.
- `build` writes anything: CR or LF in a value injects a header, a `>` in the URI breaks
  the link, an invalid parameter name is copied as is, star values are quoted (RFC 8187
  forbids it), and a link without `rel` (a MUST in section 3.3) is accepted.
- Several header lines can only be passed pre-joined.

## Sources (fetched 2026-10-13)

- RFC 8288, https://www.rfc-editor.org/rfc/rfc8288.txt: ABNF (section 3), target and
  context (3.1, 3.2), relation types and their grammar (2.1, 3.3), target attributes and
  their duplicate rules (3.4), examples (3.5), parsing algorithms (Appendix B). Errata
  page https://www.rfc-editor.org/errata/rfc8288 read: 5878 (verified) moves the star
  parameter processing of B.2 to the target attributes; 5319 (verified) defines LOALPHA as
  `%x61-7A`; 9091 (reported) asks for ASCII case-insensitive comparison of relation types.
- RFC 8187, https://www.rfc-editor.org/rfc/rfc8187.txt: ext-value grammar (3.2.1), UTF-8
  required and ISO-8859-1 encouraged, no quoted-string form (3.2.2), examples (3.2.3).
- RFC 3986, https://www.rfc-editor.org/rfc/rfc3986.txt: reference resolution (5.2) and the
  normal and abnormal examples (5.4), the component regex (Appendix B), URI characters.
- RFC 9110, https://www.rfc-editor.org/rfc/rfc9110.txt: token, quoted-string, OWS (5.6).
- IANA Link Relation Types, https://www.iana.org/assignments/link-relations/link-relations-1.csv
  (registry last updated 2026-06-12, 134 names). Finding: `openid2.local_id` is
  registered although `_` is outside the reg-rel-type rule, so strict mode accepts
  registered names as well as the grammar.
- GitHub REST docs, `content/rest/using-the-rest-api/using-pagination-in-the-rest-api.md`
  in github/docs at commit ee5047f7bbddca0ec9a7fd014d7e9efbc0d5e055 (CC-BY-4.0): two
  pagination `link` headers. Two live headers from `api.github.com` fetched this run are
  cited in the tests with their request URL.
- None of these files is committed. `tests/upstream/MANIFEST.json` records URL, revision,
  size, sha256 and licence, `scripts/fetch_upstream.py` fetches and checks them into the
  ignored `tests/upstream/` folder, and their tests skip while they are absent. The IANA
  file changes when the registry does: the fetch script then reports the mismatch and the
  manifest is refreshed by hand. The names shipped in the package are facts from a
  registry dedicated to the public domain; no descriptions are copied.

## Ranked improvements

1. **Ordered parameters.** `Link` keeps every parameter in order (`pairs`), `params` is the
   first-wins view, `hreflangs` lists every language. `Link` is frozen and hashable and
   names are lower-cased on construction. `parse(build(links)) == links` holds for any
   valid link.
2. **Grammar-driven parser.** Unquoted values run to `;` or `,` (B.3) with trailing space
   trimmed, one header line or a list of lines, the lenient resync at the next comma kept
   so one broken link never hides the next. `bytes` gets a clear `TypeError`.
3. **Strict mode.** `parse(h, strict=True)` raises `LinkError` with the offset for
   anything outside the ABNF, a missing or repeated `rel`, repeated `media`, `title`,
   `title*` or `type`, relation types that are neither reg-rel-type, registered nor
   absolute URIs, and malformed or quoted star values.
4. **RFC 8187.** `decode_ext_value` (UTF-8 and ISO-8859-1, language kept) and
   `encode_ext_value`; `Link.title` and `Link.get` prefer the star form and fall back on a
   decoding error, as section 3.4.2 allows.
5. **Resolution.** `resolve_uri` implements RFC 3986 section 5.2 exactly; `Link.resolve`
   resolves target and anchor against the base, `Link.context` gives the link context.
6. **Safe builder.** Refuses controls, non-ASCII values (pointing to `encode_ext_value`),
   URIs with `<`, `>` or whitespace, names that are not tokens, a missing `rel`, and star
   values that are not ext-values; star values are written unquoted.
7. **Relation types.** `REGISTERED_RELATIONS`, `is_registered`, `rels` lower-cases
   registered names and keeps extension URIs as written, `find` and `find_all`.
8. **Command line.** `weblink` reads a header value or a whole `curl -i` dump and prints
   the links as JSON, with `--base` and `--strict`. Debugging pagination from a shell is
   the one place a parser is needed without Python code around it.
9. **Contracts.** The RFC examples, the 3986 resolution table, the RFC 8187 examples, the
   IANA names and the GitHub headers are read from the pinned files; README examples run;
   types are checked with mypy; the installed wheel and its console script are driven
   from an empty folder.
10. **Docs and packaging.** README with executed examples and an API table, CHANGELOG,
    keywords and classifiers, sdist without planning notes or fetched files.

## Out of scope

- HTML `<link>` elements and the JSON linkset format (RFC 9264): other serialisations
  with their own parsers.
- Fetching or following links: the library stays offline and dependency-free.
- `hreflang` and `media` value validation (BCP 47, media queries): large grammars of their
  own; they are passed through.
- IRI to URI conversion (RFC 3987): targets are kept as written.
