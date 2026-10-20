# weblinking

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Parse, validate, resolve and build the HTTP `Link` header (RFC 8288), with RFC 8187
titles, typed and zero-dependency.

APIs announce pagination, alternates and related resources in the `Link` response header
(`<https://api.example.com/items?page=2>; rel="next"`). Reading it looks easy until a
title holds a comma, a server repeats `hreflang`, a title arrives percent-encoded as
`title*`, a target is relative, or a relation type comes in upper case. Writing it is
worse: a value with a line break injects a header. `weblinking` reads the header the way
RFC 8288 describes, resolves targets as RFC 3986 says, and refuses to write anything a
header cannot carry.

## Install

```
pip install weblinking
```

## Quick start

Read the pagination links an API sends:

```python
from weblinking import find, parse

header = (
    '<https://api.example.com/items?page=2>; rel="next", '
    '<https://api.example.com/items?page=5>; rel="last"'
)
links = parse(header)
print(find(links, "next").uri)
# https://api.example.com/items?page=2
print([link.rel for link in links])
# ['next', 'last']
```

Several header lines go in as a list, and each link keeps every parameter in order.
Accessors cover the parameters RFC 8288 defines; `title` decodes `title*` when the
server sent one, and relation types compare case-insensitively (ASCII letters only),
as RFC 8288 requires for registered names and extension URIs alike:

```python
from weblinking import parse

lines = [
    "</TheBook/chapter4>; rel=\"Next\"; title*=UTF-8'de'n%c3%a4chstes%20Kapitel",
    '</fr>; rel="alternate"; hreflang=fr; hreflang=fr-CA; type="text/html"',
]
chapter, french = parse(lines)
print(chapter.title, chapter.rels, chapter.has_rel("next"))
# nächstes Kapitel ('next',) True
print(french.hreflangs, french.type)
# ('fr', 'fr-CA') text/html
print(french.pairs[:2])
# (('rel', 'alternate'), ('hreflang', 'fr'))
```

Relative targets and anchors resolve against the URL of the response, following
RFC 3986 section 5 exactly:

```python
from weblinking import parse

(link,) = parse('<../terms>; rel="copyright"; anchor="#foo"')
resolved = link.resolve("https://example.com/docs/page")
print(resolved.uri)
# https://example.com/terms
print(link.context("https://example.com/docs/page"))
# https://example.com/docs/page#foo
```

Parsing is tolerant by default: a link that cannot be read is skipped up to the next
comma, so it does not hide the links after it. `strict=True` checks the RFC 8288
grammar instead and raises `LinkError`, a `ValueError` carrying the offset:

```python
from weblinking import LinkError, parse

print(len(parse('junk, <https://a.example/>; rel="next"')))
# 1
try:
    parse('<https://a.example/>; rel="next"; rel="prev"', strict=True)
except LinkError as error:
    print(error.message, error.position)
# parameter 'rel' appears more than once 0
```

`build` writes links back. It refuses what a header cannot carry (line breaks and
other control characters, non-ASCII text, a target that is not a URI reference, a link
without `rel`), so a value from user input cannot inject a header line. Text beyond
ASCII goes in a starred parameter:

```python
from weblinking import Link, build, encode_ext_value

title = encode_ext_value("nächstes Kapitel", "de")
print(build([Link("/chapter4", {"rel": "next", "title*": title})]))
# </chapter4>; rel="next"; title*=UTF-8'de'n%C3%A4chstes%20Kapitel
print(build([Link("/b", [("rel", "alternate"), ("hreflang", "en"), ("hreflang", "fr")])]))
# </b>; rel="alternate"; hreflang="en"; hreflang="fr"
```

`parse(build(links)) == links` holds for every link `build` accepts.

## Command line

`weblinking` prints the links of a header value, or of a whole response head, as ASCII
JSON. In a head only `Link` fields count, the body after the blank line is ignored, and
after redirects (`curl -sIL`) the final response wins:

```
curl -sI "https://api.github.com/repos/python/cpython/tags?per_page=5" | weblinking
weblinking --base https://example.com/a/ '<../b>; rel="up"'
```

`--strict` rejects input outside RFC 8288; errors exit with status 2. When the reader
stops early (`| head`), the command stops quietly with status 1.

## API

| Name | What it does |
| --- | --- |
| `parse(header, *, strict=False)` | Field value, or list of them, to `list[Link]` |
| `build(links)` | `Link` objects to a field value, refusing unsafe input |
| `Link(uri, params=())` | Immutable link: `uri`, `pairs`, `params`, `get`, `get_all`, `rel`, `rels`, `has_rel`, `rev`, `anchor`, `title`, `type`, `media`, `hreflang`, `hreflangs`, `resolve`, `context` |
| `LinkError` | `ValueError` for input outside the grammar, with `message` and `position` |
| `find(links, relation_type)` / `find_all(links, relation_type)` | The first link, or every link, with a relation type |
| `resolve_uri(reference, base)` | RFC 3986 section 5.2 resolution (strict form) |
| `decode_ext_value(text)` / `encode_ext_value(value, language="")` | RFC 8187 values such as `title*` |
| `ExtValue` | Decoded value, language tag and charset |
| `REGISTERED_RELATIONS` / `is_registered(relation_type)` | Names in the IANA link relation registry |

## Standards

- RFC 8288 (Web Linking): the field grammar, the duplicate rules for `rel`, `media`,
  `title`, `title*` and `type`, relation types (registered or absolute URIs). Lenient
  parsing follows the Appendix B algorithm, except that unreadable text is skipped up
  to the next comma instead of ending the parse; starred values are decoded by the
  accessors, so `pairs` keeps them as sent.
- Strict mode follows the ABNF with one documented choice: a registered relation type
  is accepted in any case (`rel=Next`), since section 2.1.1 compares them that way.
  Targets and anchors get a structural RFC 3986 URI-reference check; the inside of an
  IP literal is not checked further.
- RFC 8187: UTF-8 and ISO-8859-1 ext-values (other charsets are refused, and the
  language tag is checked lightly rather than against RFC 5646), never quoted when built.
- RFC 3986 section 5: every example of section 5.4 is part of the test suite.
- The IANA "Link Relation Types" registry as of 2026-06-12. One registered name,
  `openid2.local_id`, falls outside the `reg-rel-type` rule; strict mode accepts it.

The tests read these documents from local copies that `python scripts/fetch_upstream.py`
downloads and checks against `tests/upstream/MANIFEST.json`.

## Why not something else

Checked on 2026-10-19 by running each one:

- `requests` 2.34.2 and `httpx` 0.28.1 expose `Response.links`, a dict keyed by relation
  type: a second link with the same `rel` replaces the first, a target holding `;` is
  cut there, and `title*` stays percent-encoded. There is no builder.
- `httplink` 0.2.0 (last release 2020) only parses, and rejects a `title*` without a
  language tag (`UTF-8''...`), which RFC 8187 allows.
- `LinkHeader` 0.4.3 (last release 2015) follows RFC 5988, which RFC 8288 replaced.
- `ietfparse` 1.9.0 covers many RFCs; its `parse_link` fails on an empty quoted value or
  an `=` inside one, keeps the backslashes of escaped quotes, and lower-cases values,
  and its link formatter writes a `"` inside a value without escaping it.

`weblinking` does this one header, both directions, with strict and tolerant reading,
RFC 8187 values, RFC 3986 resolution, full type hints and no dependencies. Its parser is
checked against `requests`, `httplink`, `ietfparse` and the `http-link-header` package
for Node.js; see [CERT-1.0-REPORT.md](https://github.com/JaviLianes8/weblink/blob/main/CERT-1.0-REPORT.md).

## Documentation

- [GUIDE.md](https://github.com/JaviLianes8/weblink/blob/main/GUIDE.md): every rule the library follows, the errors it
  raises and what is stable.
- [CHANGELOG.md](https://github.com/JaviLianes8/weblink/blob/main/CHANGELOG.md): what changed in each release.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/weblink/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
