"""Seeded generator of Link header values inside the RFC 8288 grammar, for oracle tests.

Hand-written from the ABNF of RFC 8288 section 3 (link-value, link-param), RFC 9110
section 5.6 (token, quoted-string, OWS, BWS) and RFC 8187 section 3.2 (ext-value). Each
header comes with the pairs a reader must find in it, worked out here independently of
the library: quoted-pairs undone, names lower-cased, starred values kept as sent.
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field

TCHAR = "!#$%&'*+-.^_`|~" + string.digits + string.ascii_letters
ATTR_CHAR = string.ascii_letters + string.digits + "!#$&+-.^_`|~"
# Visible ASCII and space; quote and backslash only ever appear escaped.
QDTEXT = "".join(chr(c) for c in range(0x20, 0x7F))
REGISTERED = ("next", "prev", "last", "first", "alternate", "canonical", "stylesheet", "up")
SINGLE = ("rel", "media", "title", "title*", "type")
UNICODE = "aZ09 ,;%'\"äé€\U0001f600"


@dataclass
class Header:
    text: str
    plain: bool = False
    links: list[tuple[str, list[tuple[str, str]]]] = field(default_factory=list)


def _ows(rng: random.Random, out: Header) -> str:
    return rng.choice(("", " ") if out.plain else ("", "", " ", "  ", "\t", " \t"))


def _token(rng: random.Random, alphabet: str = TCHAR, size: int = 8) -> str:
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(1, size)))


def _quoted(rng: random.Random, value: str, out: Header) -> str:
    chars = []
    for c in value:
        # Any visible character may be sent as a quoted-pair; quote and backslash must be.
        escape = c in '"\\' or (rng.random() < 0.05 and not out.plain)
        chars.append("\\" + c if escape else c)
    return '"' + "".join(chars) + '"'


def _uri(rng: random.Random, out: Header) -> str:
    seg = string.ascii_letters + string.digits + "-._~!$&*+:@" + ("" if out.plain else "'(),;=")
    lead = rng.choice(("", "https://h.test/", "//h.test:8080/", "urn:x:", "../", "./", "/"))
    # A colon in the first segment of a relative path would read as a scheme.
    first = seg.replace(":", "") if lead in ("", "/") else seg
    # After a lone "/" an empty segment would start an authority.
    keep = lead == "/" or out.plain or rng.random() < 0.8
    parts = [lead, _token(rng, first, 6) if keep else ""]
    parts += ["/" + _token(rng, seg, 6) for _ in range(rng.randint(0, 2))]
    if rng.random() < 0.4:
        parts.append("?" + _token(rng, seg + "/?", 10))
    if rng.random() < 0.3:
        parts.append("#" + _token(rng, seg + "/?", 6))
    return "".join(parts)


def _rel(rng: random.Random, out: Header) -> str:
    kinds = (
        lambda: rng.choice(REGISTERED),
        lambda: rng.choice(REGISTERED).upper(),
        lambda: _token(rng, "abcxyz", 1) + _token(rng, "abz09.-", 6),
        lambda: "https://e.test/rel/" + _token(rng, string.ascii_lowercase, 5),
    )
    count = 1 if out.plain else rng.randint(1, 3)
    return " ".join(rng.choice(kinds)() for _ in range(count))


def _ext_value(rng: random.Random) -> str:
    text = "".join(rng.choice(UNICODE) for _ in range(rng.randint(1, 6)))
    encoded = "".join(
        chr(b) if chr(b) in ATTR_CHAR else rng.choice(("%{:02X}", "%{:02x}")).format(b)
        for b in text.encode("utf-8")
    )
    charset = rng.choice(("UTF-8", "utf-8", "Utf-8"))
    language = rng.choice(("", "en", "de", "DE", "fr-CA"))
    return f"{charset}'{language}'{encoded}"


def _value(rng: random.Random, name: str, out: Header) -> str:
    if name == "rel":
        return _rel(rng, out)
    if name == "hreflang":
        return rng.choice(("en", "fr", "fr-CA", "de-AT"))
    if name == "type":
        return rng.choice(("text/html", "application/json", "text"))
    if name == "anchor":
        return _uri(rng, out)
    if out.plain:
        return _token(rng, string.ascii_letters + string.digits + "-._~")
    return rng.choice((_token(rng), "".join(rng.choice(QDTEXT) for _ in range(6)), ""))


def _param(rng: random.Random, name: str, out: Header) -> tuple[str, str, str]:
    """(name as written, value as read, value as written)."""
    if name == "title*":
        value = wire = _ext_value(rng)
    else:
        value = _value(rng, name, out)
        bare = value and all(c in TCHAR for c in value) and rng.random() < 0.5
        wire = value if bare else _quoted(rng, value, out)
    written = "".join(c.upper() if rng.random() < 0.3 else c for c in name)
    return written, value, wire


def header(rng: random.Random, *, tight: bool = False, plain: bool = False) -> Header:
    """One field value of 1 to 4 links, each with a rel and up to 6 more parameters.

    ``tight`` leaves out the optional whitespace after values (before ``;`` and ``,``),
    which some readers keep as part of an unquoted value. ``plain`` keeps to what simple
    readers handle: values without whitespace, delimiters, quotes or escapes, each
    parameter once, URIs without ``'(),;=``, spaces as the only whitespace.
    """
    out = Header("", plain=plain)
    values = []
    for _ in range(rng.randint(1, 4)):
        names = ["rel"]
        for _ in range(rng.randint(0, 6)):
            pick = rng.choice(("title", "title*", "hreflang", "type", "media", "anchor", "x"))
            if pick == "x":
                pick = "x-" + _token(rng, string.ascii_lowercase + "-", 5)
            if pick in names and (plain or pick in SINGLE):
                continue
            names.append(pick)
        rng.shuffle(names)
        uri = _uri(rng, out)
        pairs, chunks = [], [f"<{uri}>"]
        for name in names:
            written, value, wire = _param(rng, name, out)
            pairs.append((written.lower(), value))
            before = "" if tight else _ows(rng, out)
            ows = [_ows(rng, out) for _ in range(3)]
            chunks.append(f"{before};{ows[0]}{written}{ows[1]}={ows[2]}{wire}")
        out.links.append((uri, pairs))
        values.append("".join(chunks))
    comma = ("" if tight else _ows(rng, out)) + "," + _ows(rng, out)
    out.text = _ows(rng, out) + comma.join(values) + _ows(rng, out)
    return out
