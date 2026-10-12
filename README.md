# weblink

Parse and build the HTTP Link header (RFC 8288), typed and zero-dependency

## Install

```
pip install weblink
```

## Usage

Parse a `Link` header, such as the one REST APIs send for pagination:

```python
from weblink import parse

header = (
    '<https://api.example.com/items?page=2>; rel="next", '
    '<https://api.example.com/items?page=5>; rel="last"'
)

links = parse(header)
next_url = next(link.uri for link in links if "next" in link.rels)
# "https://api.example.com/items?page=2"
```

Each parsed link is a `Link` with a `uri` and a `params` dict, plus typed
accessors for the common parameters:

```python
link = parse('<https://example.com/fr>; rel="alternate"; type="text/html"; hreflang="fr"')[0]
link.uri        # "https://example.com/fr"
link.rel        # "alternate"
link.rels       # ("alternate",)
link.type       # "text/html"
link.hreflang   # "fr"
link.params     # {"rel": "alternate", "type": "text/html", "hreflang": "fr"}
```

Build a header value back from links. Parameter values are quoted and escaped,
so the output parses back to the same links:

```python
from weblink import Link, build

build([
    Link("https://api.example.com/items?page=2", {"rel": "next"}),
    Link("https://api.example.com/items?page=1", {"rel": "prev"}),
])
# '<https://api.example.com/items?page=2>; rel="next", <https://api.example.com/items?page=1>; rel="prev"'
```

Parsing is tolerant: commas inside quoted values or angle bracketed URIs never
split a link, and segments that cannot be read are skipped rather than raising.

## Why

The `Link` header (RFC 8288) is how APIs expose pagination and relations, yet
there is no small, typed, zero-dependency library that both parses and builds
it. `requests` keeps its parser private, `httplink` only parses and has not been
released since 2020, `LinkHeader` cites the superseded RFC 5988 and was last
touched in 2015, and `ietfparse` is a broad multi-RFC parser. `weblink` does one
job, both directions, with full type hints and nothing to install alongside it.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
