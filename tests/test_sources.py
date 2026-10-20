"""Check the library against RFC 8288, RFC 8187, RFC 3986, RFC 9110 and the IANA registry.

The files are read from tests/upstream (URL, size and sha256 in MANIFEST.json); the tests
that read them skip until `python scripts/fetch_upstream.py` has fetched them.
"""

from __future__ import annotations

import csv
import io
import re
import string

import pytest

from weblinking import (
    REGISTERED_RELATIONS,
    Link,
    LinkError,
    build,
    decode_ext_value,
    parse,
    resolve_uri,
)
from weblinking._chars import is_qdtext


def _section(text: str, title: str, end: str) -> str:
    """The body of a section: its last heading (the first is in the contents) to ``end``."""
    body = text.rsplit(title, 1)[1].split(end, 1)[0]
    # Drop the page footer and header that interrupt the text every page.
    return re.sub(r"\n+\S[^\n]*\[Page \d+\]\n\x0c?\n?RFC \d+ [^\n]*\n+", "\n\n", body)


def _link_examples(rfc8288: str) -> list[str]:
    section = _section(rfc8288, "3.5.  Link Header Field Examples", "4.  IANA Considerations")
    blocks = re.findall(r"^   Link: (.+(?:\n {9}\S.*)*)", section, flags=re.MULTILINE)
    return [" ".join(part.strip() for part in block.split("\n")) for block in blocks]


def test_the_section_3_5_examples_parse_strictly(rfc8288: str) -> None:
    examples = _link_examples(rfc8288)
    assert len(examples) == 8
    for example in examples:
        assert parse(example, strict=True), example


def test_the_section_3_5_examples_mean_what_the_rfc_says(rfc8288: str) -> None:
    # Expected values from https://www.rfc-editor.org/rfc/rfc8288.txt section 3.5.
    first, ext, anchored, german, multi, joined, start, index = map(parse, _link_examples(rfc8288))
    assert first[0].title == "previous chapter" and first[0].rels == ("previous",)
    assert ext[0].rels == ("http://example.net/foo",)
    assert anchored[0].context("http://example.com/doc") == "http://example.com/doc#foo"
    assert [link.title for link in german] == ["letztes Kapitel", "nächstes Kapitel"]
    assert decode_ext_value(german[1].get_all("title*")[0]).language == "de"
    assert multi[0].rels == ("start", "http://example.net/relation/other")
    assert joined == start + index


def test_the_examples_round_trip_through_build(rfc8288: str) -> None:
    for example in _link_examples(rfc8288):
        links = parse(example, strict=True)
        assert parse(build(links), strict=True) == links


def test_the_rfc_8187_examples_decode(rfc8187: str) -> None:
    section = _section(rfc8187, "3.2.3.  Examples", "4.  Guidelines")
    values = re.findall(r"^ +foo: bar; title\*=(\S+)$", section, flags=re.MULTILINE)
    # Expected text from https://www.rfc-editor.org/rfc/rfc8187.txt section 3.2.3.
    assert [decode_ext_value(value) for value in values] == [
        ("£ rates", "en", "UTF-8"),
        ("£ and € rates", "", "UTF-8"),
    ]


def test_ext_values_accept_exactly_the_rfc_8187_attr_chars(rfc8187: str) -> None:
    rule = rfc8187.split("attr-char     =", 1)[1].split("; token except", 1)[0]
    allowed = set(re.findall(r'"(.)"', rule)) | set(string.ascii_letters + string.digits)
    assert len(allowed) == 62 + 12
    for code in range(0x21, 0x7F):
        char = chr(code)
        if char in "%'":
            continue
        try:
            decode_ext_value(f"UTF-8''{char}")
        except LinkError:
            assert char not in allowed, char
        else:
            assert char in allowed, char


def test_the_rfc_3986_resolution_examples(rfc3986: str) -> None:
    section = _section(rfc3986, "5.4.  Reference Resolution Examples", "6.  Normalization")
    (base,) = re.findall(r"base URI of\s+(\S+)", section)
    pairs = re.findall(r'^ +"([^"]*)" += +"([^"]*)"', section, flags=re.MULTILINE)
    assert base == "http://a/b/c/d;p?q"
    assert len(pairs) == 42
    for reference, expected in pairs:
        assert resolve_uri(reference, base) == expected, reference


def test_relative_targets_resolve_as_rfc_8288_section_3_1_requires(rfc3986: str) -> None:
    pairs = re.findall(r'^ +"([^"]*)" += +"([^"]*)"', rfc3986, flags=re.MULTILINE)
    for reference, expected in pairs:
        if ">" in reference or " " in reference:
            continue
        (link,) = parse(f'<{reference}>; rel="next"; anchor="{reference}"')
        resolved = link.resolve("http://a/b/c/d;p?q")
        assert resolved.uri == resolved.anchor == expected, reference


def _registry_names(iana_csv: str) -> set[str]:
    return {row["Relation Name"] for row in csv.DictReader(io.StringIO(iana_csv))}


def test_the_shipped_names_match_the_iana_registry(iana_csv: str) -> None:
    assert _registry_names(iana_csv) == REGISTERED_RELATIONS


def test_every_registered_name_passes_strict_parsing_in_any_case(iana_csv: str) -> None:
    for name in sorted(_registry_names(iana_csv)):
        for spelled in (name, name.upper()):
            (link,) = parse(f"</>; rel={spelled}", strict=True)
            assert link.has_rel(name) and link.rels == (name,)


def test_a_registered_name_outside_the_reg_rel_type_rule_is_accepted(iana_csv: str) -> None:
    outside = {n for n in _registry_names(iana_csv) if not re.fullmatch(r"[a-z][a-z0-9.\-]*", n)}
    assert outside == {"openid2.local_id"}
    assert build([Link("/", {"rel": "openid2.local_id"})]) == '</>; rel="openid2.local_id"'
    with pytest.raises(LinkError):
        parse("</>; rel=unregistered_name", strict=True)


def test_parameter_names_are_exactly_the_rfc_9110_tokens(rfc9110: str) -> None:
    rule = rfc9110.split("tchar          =", 1)[1].split("; any VCHAR", 1)[0]
    tchar = set(re.findall(r'"(.)"', rule)) | set(string.ascii_letters + string.digits)
    assert len(tchar) == 77
    for code in range(0x21, 0x100):
        char = chr(code)
        try:
            build([Link("/", [("rel", "next"), (char, "UTF-8''x")])])
        except LinkError:
            assert char not in tchar, repr(char)
        else:
            assert char in tchar, repr(char)


def test_quoted_values_accept_exactly_the_rfc_9110_qdtext(rfc9110: str) -> None:
    rule = re.findall(r"qdtext +=(.+)", rfc9110)[0]
    assert rule.split() == [
        "HTAB",
        "/",
        "SP",
        "/",
        "%x21",
        "/",
        "%x23-5B",
        "/",
        "%x5D-7E",
        "/",
        "obs-text",
    ]
    assert re.findall(r"obs-text +=(.+)", rfc9110)[0].split() == ["%x80-FF"]
    qdtext = {0x09, 0x20, 0x21, *range(0x23, 0x5C), *range(0x5D, 0x7F), *range(0x80, 0x100)}
    assert [code for code in range(0x180) if is_qdtext(chr(code))] == sorted(qdtext)
    for code in range(0x180):
        try:
            parse(f'</>; rel=next; x="{chr(code)}"', strict=True)
        except LinkError:
            assert code not in qdtext, hex(code)
        else:
            assert code in qdtext, hex(code)


def test_the_github_pagination_headers(github_docs: str) -> None:
    headers = re.findall(r"^link: (.+)$", github_docs, flags=re.MULTILINE)
    assert len(headers) == 2
    first, second = (parse(header, strict=True) for header in headers)
    assert [link.rel for link in first] == ["prev", "next", "last", "first"]
    assert [link.rel for link in second] == ["next", "last"]
    assert all(build(parse(header)) == header for header in headers)
