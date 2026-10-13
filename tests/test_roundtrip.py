"""Seeded random links: whatever build accepts, strict parse reads back unchanged."""

from __future__ import annotations

import random
import string

from weblink import Link, LinkError, build, encode_ext_value, parse

_PCHAR = string.ascii_letters + string.digits + "-._~!$&'()*+,;=:@/"
_PREFIXES = ["", "/", "./", "https://h.test/", "//u@h.test:8080/", "https://[2001:db8::1]/", "urn:"]
_NAMES = ["rel", "title", "type", "hreflang", "anchor", "media", "x-ext", "title*", "ext*"]
_TEXT = "\t !#$%&'()*+,-./:;<=>?@[]^_`{|}~\"\\" + string.ascii_letters + string.digits


def _random_link(rng: random.Random) -> Link:
    prefix = rng.choice(_PREFIXES)
    # Without a prefix the first segment must not hold a colon (RFC 3986 path-noscheme).
    chars = _PCHAR.replace(":", "") if prefix == "" else _PCHAR
    uri = prefix + "".join(rng.choice(chars) for _ in range(rng.randrange(0, 20)))
    uri += rng.choice(["", "?", "?a=1&b=:/?", "#", "#f/?", "?q#f"])
    pairs = [("rel", rng.choice(["next", "Prev last", "https://e.test/r", "a.b-c  d"]))]
    for _ in range(rng.randrange(0, 5)):
        name = rng.choice(_NAMES[1:])
        text = "".join(rng.choice(_TEXT) for _ in range(rng.randrange(0, 12)))
        if name.endswith("*"):
            text = encode_ext_value(text + rng.choice(["", "é", "€"]), rng.choice(["", "de"]))
        elif name == "anchor":
            text = "#" + "".join(rng.choice(string.ascii_letters) for _ in range(5))
        pairs.append((name, text))
    return Link(uri, pairs)


def test_random_links_round_trip_through_strict_parsing() -> None:
    rng = random.Random(8288)
    built = 0
    for _ in range(3000):
        links = [_random_link(rng) for _ in range(rng.randrange(1, 4))]
        try:
            header = build(links)
        except LinkError as error:
            assert "more than once" in str(error), error
            continue
        assert parse(header, strict=True) == links, header
        assert parse(header) == links, header
        built += 1
    assert built > 1500
