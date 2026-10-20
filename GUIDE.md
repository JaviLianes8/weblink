# weblinking guide

Everything `weblinking` does, the rules behind it and what 1.0.0 promises to keep. Every
example below runs as part of the test suite and prints what its comment shows.

## Reading a header

`parse(header, *, strict=False)` takes one field value, or an iterable of them (one per
header line), and returns a `list[Link]` in the order the links appear. A quoted string
never continues into the next line.

The default mode is tolerant, for reading what servers really send. It follows the
algorithm of RFC 8288 Appendix B: an unquoted value runs to the next `;` or `,`, an
unclosed quoted value runs to the end of its line, parameter names are lower-cased and
empty names are dropped. Text that cannot be read is skipped up to the next comma, so it
never hides the links that follow; quotes and brackets inside such text are ignored.

```python
from weblinking import parse

print(parse('<a>; rel=next junk; title="t", <b>; rel=prev'))
# [Link('a', {'rel': 'next junk', 'title': 't'}), Link('b', {'rel': 'prev'})]
print(parse(['</a>; rel=next; title="open', "</b>; rel=prev"]))
# [Link('/a', {'rel': 'next', 'title': 'open'}), Link('/b', {'rel': 'prev'})]
```

`strict=True` checks the RFC 8288 grammar (with the RFC 9110 rules for tokens, quoted
strings and whitespace) and raises `LinkError` at the first problem. It also enforces the
rules of RFC 8288 sections 3.3 and 3.4: a `rel` is required; `rel`, `media`, `title`,
`title*` and `type` may appear once; relation types (in `rel` and `rev`) are registered
names, `reg-rel-type` names in lower case, or absolute URIs; targets and anchors are
RFC 3986 URI references; starred values are not quoted and must decode by the rules of
`decode_ext_value` below. A
registered relation type is accepted in any case (`rel=Next`), since RFC 8288 compares
registered names without case. What strict mode accepts, tolerant mode reads the same way.

```python
from weblinking import LinkError, parse

try:
    parse('</a>; rel=next; title="x"; title="y"', strict=True)
except LinkError as error:
    print(error.message, error.position)
# parameter 'title' appears more than once 0
```

`position` is the offset in the line being read: the character where the grammar broke,
or the start of the link when a rule about the whole link failed.

## The Link object

`Link(uri, params=())` holds a target and its parameters in order. `params` is a mapping
or an iterable of `(name, value)` pairs (tuples, or lists as JSON gives them). The ASCII
letters of names are lower-cased and no other character folds, so a name written with
the Kelvin sign (U+212A) for its `K` never turns into a token such as `key`; values are kept
exactly as given. Links are immutable (attributes can be neither set nor deleted),
hashable, picklable, and equal when their target and pairs are equal, in order.

- `uri` is the target as written; `pairs` is every parameter in order, repeats included.
- `params` is a new dict on each access; when a name repeats, its first value wins.
- `get_all(name)` gives every raw value of a parameter, matching names the same way;
  `get(name)` gives the first, but
  prefers a decodable RFC 8187 `name*` form as RFC 8288 section 3.4 asks (only the
  first starred value is tried; when it cannot be decoded the plain value is used).
- `rel` is the first raw `rel` value (a `rel*` parameter never replaces it); `rels` splits
  it on runs of spaces and tabs (and the CR and LF tolerant parsing skips, never other
  whitespace such as a no-break space) and lower-cases the ASCII letters of each type;
  `has_rel(relation_type)` compares the same way. Only ASCII letters fold, so a look
  alike such as the Kelvin sign never matches `k`. Extension types (absolute URIs)
  compare without case too, as RFC 8288 section 2.1.2 says.
- `rev`, `anchor`, `type`, `media` and `hreflang` give the first raw value (so the
  first `anchor` is the context);
  `hreflangs` gives every `hreflang`; `title` is `get("title")`.

```python
from weblinking import parse

header = (
    '</de>; rel=alternate; hreflang=de; hreflang=de-AT; title="Deutsch"; '
    "title*=UTF-8'de'Deutsch%20%C3%BCbersicht"
)
(link,) = parse(header)
print(link.title, "|", link.get("title*"))
# Deutsch übersicht | UTF-8'de'Deutsch%20%C3%BCbersicht
print(link.hreflang, link.hreflangs, link.has_rel("ALTERNATE"))
# de ('de', 'de-AT') True
```

`find(links, relation_type)` returns the first link carrying a relation type, or `None`;
`find_all(links, relation_type)` returns all of them in order.

## RFC 8187 values

`decode_ext_value(text)` reads `charset'language'value-chars` into an `ExtValue` with
`value`, `language` and `charset`. UTF-8 and ISO-8859-1 are read, in any case; `charset`
is reported as `"UTF-8"` or `"ISO-8859-1"`. Other charsets the RFC 8187 grammar allows,
such as `US-ASCII`, are refused, and so are escaped octets the charset cannot decode. The
language is checked lightly (letters, digits and hyphens, not starting with a hyphen),
not against the full RFC 5646 grammar. `encode_ext_value(value, language="")`
writes UTF-8, percent-encoding every octet outside `attr-char` with upper-case hex.

```python
from weblinking import decode_ext_value, encode_ext_value

print(decode_ext_value("iso-8859-1'en'%A3%20rates"))
# ExtValue(value='£ rates', language='en', charset='ISO-8859-1')
print(encode_ext_value("50 €", "en"))
# UTF-8'en'50%20%E2%82%AC
```

## Resolving targets

Relative targets and anchors are resolved against the URL of the response, as RFC 8288
sections 3.1 and 3.2 require. `resolve_uri(reference, base)` follows RFC 3986 section 5.2
in its strict form: a reference with a scheme is never relative, so `http:g` stays
`http:g`. Text before the first colon that is not a valid scheme does not make one, so
`a b:c` resolves as a relative path. Nothing is normalised beyond dot segments. The base
must be an absolute URI.

`Link.resolve(base)` returns a copy with the target and every `anchor` resolved;
`Link.context(base)` returns the link context, the first `anchor` resolved, or the base.

```python
from weblinking import Link, resolve_uri

print(resolve_uri("g;x=1/../y", "http://a/b/c/d;p?q"))
# http://a/b/c/y
link = Link("../b", {"rel": "up", "anchor": "#s"}).resolve("https://h.test/a/c")
print(link.uri, link.context("https://h.test/a/c"))
# https://h.test/b https://h.test/a/c#s
```

## Writing a header

`build(links)` writes `<uri>; name="value"` for each link and joins them with `", "`.
Values are quoted, with `"` and `\` escaped; starred values are written bare. It raises
`LinkError` for every link strict parsing would refuse and for values holding control
characters or anything beyond ASCII, which could break or inject header lines. Send such
text as `title*` with `encode_ext_value`. For every list `build` accepts,
`parse(build(links), strict=True) == links`.

```python
from weblinking import Link, LinkError, build

try:
    build([Link("/a", {"rel": "next", "title": "a\r\nSet-Cookie: x=y"})])
except LinkError as error:
    print(error)
# 'title' value has '\r'; send non-ASCII text as 'title*' with encode_ext_value
```

## Relation types

`REGISTERED_RELATIONS` is the frozenset of the 134 names in the IANA "Link Relation
Types" registry as updated on 2026-06-12, all lower case. `is_registered(relation_type)` looks a
name up without ASCII case. One registered name, `openid2.local_id`, falls outside the
`reg-rel-type` rule; strict mode accepts it because it is registered.

```python
from weblinking import REGISTERED_RELATIONS, is_registered

print(is_registered("Next"), is_registered("openid2.local_id"), "preload" in REGISTERED_RELATIONS)
# True True True
```

## Errors

- `LinkError`, a subclass of `ValueError`, is raised for input outside the grammar or the
  rules above. `message` is the reason; `position` is the offset in the line for
  `parse(..., strict=True)` and `None` elsewhere. Messages quote at most 80 characters of
  the offending text (fewer when it needs escapes) and then give its length, so a huge
  input never ends up whole in a log line. When the text is a target, an anchor or a
  base URI, its userinfo, its query and its fragment show as `***`, since credentials,
  tokens and signatures travel there. The value is invalid, so its parts are not trusted:
  everything before the last `@` and everything after the first `?` or `#` is hidden,
  keeping only a leading `scheme://`.
- `TypeError` is raised for arguments of the wrong type: `bytes` instead of text, a name
  that is not a `str`, a `Link` where an iterable of links is expected, an item that is
  not a `Link`, and so on. Tolerant parsing never raises `LinkError`.

## Command line

`weblinking [HEADER] [--base URI] [--strict]` prints the links as ASCII JSON: a list of
objects with `uri`, `rels` and `params` (the pairs). Without `HEADER` it reads standard
input as ISO-8859-1 octets: either a bare header value or a response head such as
`curl -sI` prints. In a head only `Link` fields count, folded lines continue the field
before them, the body after the blank line is ignored and, after redirects, the last
response wins. Errors print `weblinking: <message>` and exit with status 2. When the
reader closes the pipe early (`weblinking ... | head`), the command stops quietly with
status 1.
`python -m weblinking` runs the same command.

## What is stable

From 1.0.0 the following follow Semantic Versioning: the names in `weblinking.__all__`,
their signatures, parameter names and defaults; the members of `Link` and the fields of
`ExtValue`; `LinkError` with `message` and `position`, and the cases that raise it or
`TypeError`; the command, its options, its JSON shape and its exit statuses. The wording
of error messages may improve in minor releases. `REGISTERED_RELATIONS` follows the IANA
registry, so a minor release may add names the registry adds. Private modules (`_*`) may
change at any time.

## Ground truth

The test suite checks the library against the RFC 8288, RFC 8187, RFC 3986 and RFC 9110
texts, the IANA registry and the GitHub pagination docs, fetched by
`python scripts/fetch_upstream.py` and verified against `tests/upstream/MANIFEST.json`;
against `httplink`, `ietfparse`, `requests` and the `http-link-header` package for
Node.js on generated headers; against a step-by-step transcription of RFC 3986 section
5.2 and the `rfc3986` package for resolution; and, with `WEBLINKING_LIVE=1`, against the
pagination headers GitHub and GitLab send.
