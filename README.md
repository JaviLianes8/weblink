# weblinking

Parse, validate, resolve and build the HTTP `Link` header (RFC 8288), with RFC 8187
titles, typed and zero-dependency.

## Install

```
pip install weblinking
```

## Usage

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

`--strict` rejects input outside RFC 8288; errors exit with status 2.

## API

| Name | What it does |
| --- | --- |
| `parse(header, *, strict=False)` | Field value, or list of them, to `list[Link]` |
| `build(links)` | `Link` objects to a field value, refusing unsafe input |
| `Link(uri, params)` | Immutable link: `uri`, `pairs`, `params`, `get`, `get_all`, `rel`, `rels`, `has_rel`, `rev`, `anchor`, `title`, `type`, `media`, `hreflang`, `hreflangs`, `resolve`, `context` |
| `LinkError` | `ValueError` for input outside the grammar, with `message` and `position` |
| `find(links, rel)` / `find_all(links, rel)` | The first link, or every link, with a relation type |
| `resolve_uri(reference, base)` | RFC 3986 section 5.2 resolution (strict form) |
| `decode_ext_value(text)` / `encode_ext_value(text, language)` | RFC 8187 values such as `title*` |
| `ExtValue` | Decoded value, language tag and charset |
| `REGISTERED_RELATIONS` / `is_registered(rel)` | Names in the IANA link relation registry |

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
- RFC 8187: UTF-8 and ISO-8859-1 ext-values, never quoted when built.
- RFC 3986 section 5: every example of section 5.4 is part of the test suite.
- The IANA "Link Relation Types" registry as of 2026-06-12. One registered name,
  `openid2.local_id`, falls outside the `reg-rel-type` rule; strict mode accepts it.

The tests read these documents from local copies that `python scripts/fetch_upstream.py`
downloads and checks against `tests/upstream/MANIFEST.json`.

## Why

The `Link` header is how APIs expose pagination and relations, yet there is no small,
typed, zero-dependency library that both parses and builds it. `requests` keeps its
parser private, `httplink` only parses and has not been released since 2020,
`LinkHeader` cites the superseded RFC 5988 and was last touched in 2015, and `ietfparse`
is a broad multi-RFC parser. `weblinking` does one job, both directions, with full type
hints and nothing to install alongside it.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
