"""Seeded hostile input: only LinkError escapes, messages stay short, results agree.

Properties checked on random text built from the characters the grammar cares about:
lenient parsing never raises; strict parsing raises only LinkError with a position on
the line; whatever strict mode accepts, lenient mode reads the same way; whatever build
accepts, both modes read back unchanged; RFC 8187 values round trip.
"""

from __future__ import annotations

import io
import json
import random
import re
import string

import pytest

from weblinking import (
    LinkError,
    build,
    decode_ext_value,
    encode_ext_value,
    find_all,
    parse,
    resolve_uri,
)
from weblinking._cli import field_values, main

# The grammar's delimiters, whitespace and line breaks, then hostile code points.
GRAMMAR = (
    "<>;,=*%/:#?.-aAzZ09'"
    + "".join(map(chr, (0x22, 0x5C, 0x20, 0x09, 0x0D, 0x0A, 0x00, 0x7F, 0x80, 0xFF, 0xE9, 0x2028)))
    + "".join(map(chr, (0xD800, 0x1F600)))
)
SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
PIECES = ["<", ">", ";", ",", "=", '"', "\\", " ", "rel", "next", "title*", "UTF-8''", "%E2"]
PIECES += ["<a>", "<https://h.test/p?q#f>", "; rel=next", '"x,y"', "%", "anchor", "#x", "Rel"]


def _text(rng: random.Random) -> str:
    if rng.random() < 0.5:
        return "".join(rng.choice(GRAMMAR) for _ in range(rng.randrange(0, 40)))
    return "".join(rng.choice(PIECES) for _ in range(rng.randrange(0, 14)))


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_parsing_hostile_text_fails_only_with_short_link_errors(seed: int) -> None:
    rng = random.Random(seed)
    accepted = 0
    for _ in range(20_000):
        text = _text(rng)
        lenient = parse(text)
        try:
            strict = parse(text, strict=True)
        except LinkError as error:
            assert error.position is not None and 0 <= error.position <= len(text), text
            assert len(str(error)) < 300 and str(error).startswith(error.message)
            continue
        accepted += 1
        assert strict == lenient, text
        for link in strict:
            assert link.rel is not None and find_all(strict, link.rels[0]) if link.rels else True
    assert accepted > 500


@pytest.mark.parametrize("seed", [4, 5])
def test_whatever_build_accepts_reads_back_unchanged(seed: int) -> None:
    rng = random.Random(seed)
    built = 0
    for _ in range(20_000):
        links = parse(_text(rng))
        try:
            header = build(links)
        except LinkError as error:
            assert len(str(error)) < 300
            continue
        built += 1
        assert parse(header, strict=True) == links, header
        assert parse(header) == links, header
    assert built > 300


@pytest.mark.parametrize("seed", [6, 7])
def test_ext_values_decode_or_fail_cleanly_and_round_trip(seed: int) -> None:
    rng = random.Random(seed)
    decoded = 0
    alphabet = "'%" + string.hexdigits + "aZ!#$&+-.^_`|~ é"
    for _ in range(20_000):
        charset = rng.choice(["UTF-8", "utf-8", "ISO-8859-1", "iso-8859-1", "latin1", ""])
        language = rng.choice(["", "en", "de-AT", "-x", "e n"])
        quotes = rng.choice(["''", "'", ""]) if rng.random() < 0.1 else "''"
        middle = quotes[:1] + language + quotes[1:]
        text = charset + middle + "".join(rng.choice(alphabet) for _ in range(rng.randrange(16)))
        try:
            value = decode_ext_value(text)
        except LinkError as error:
            assert error.position is None and len(str(error)) < 300
            continue
        decoded += 1
        assert value.charset in ("UTF-8", "ISO-8859-1")
        again = decode_ext_value(encode_ext_value(value.value, value.language))
        assert (again.value, again.language) == (value.value, value.language)
    assert decoded > 1000


@pytest.mark.parametrize("seed", [8, 9])
def test_resolution_of_hostile_references_never_crashes(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(20_000):
        reference, base = _text(rng), _text(rng)
        try:
            result = resolve_uri(reference, base)
        except LinkError as error:
            assert SCHEME.match(base) is None, base
            assert len(str(error)) < 300
            continue
        assert SCHEME.match(base) is not None
        scheme = SCHEME.match(reference)
        assert result.startswith(scheme.group() if scheme else base.partition(":")[0] + ":")


@pytest.mark.parametrize("seed", [10, 11])
def test_the_command_reads_hostile_heads(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(3_000):
        lines = [rng.choice(["HTTP/1.1 200", "Link:", "link :", " ", "", "X: y"]) + _text(rng)]
        lines += [rng.choice(["Link: ", "  ", "HTTP/2 302", ""]) + _text(rng) for _ in range(4)]
        head = rng.choice(["\r\n", "\n"]).join(lines)
        assert all(isinstance(value, str) for value in field_values(head))
        out = io.StringIO()
        status = main(["--strict"] if rng.random() < 0.5 else [], io.StringIO(head), out)
        assert status in (0, 2)
        if status == 0:
            assert out.getvalue().isascii() and isinstance(json.loads(out.getvalue()), list)
