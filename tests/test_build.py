from __future__ import annotations

import pytest

from weblinking import Link, LinkError, build, encode_ext_value, parse


def test_build_a_single_link() -> None:
    result = build([Link("https://example.com/next", {"rel": "next"})])
    assert result == '<https://example.com/next>; rel="next"'


def test_build_joins_multiple_links_with_a_comma() -> None:
    result = build(
        [
            Link("https://a.test/2", {"rel": "next"}),
            Link("https://a.test/1", {"rel": "prev"}),
        ]
    )
    assert result == '<https://a.test/2>; rel="next", <https://a.test/1>; rel="prev"'


def test_build_quotes_and_escapes_values() -> None:
    result = build([Link("https://a.test/", {"rel": "next", "title": 'a "quote"'})])
    assert result == '<https://a.test/>; rel="next"; title="a \\"quote\\""'


def test_build_accepts_the_empty_reference() -> None:
    # "<>" is a valid URI-reference: the link points at its own context.
    assert build([Link("", {"rel": "self"})]) == '<>; rel="self"'


def test_build_rejects_a_target_that_would_end_the_brackets() -> None:
    with pytest.raises(LinkError, match="URI reference"):
        build([Link("https://a.test/>; rel=evil", {"rel": "next"})])


def test_round_trip_through_parse() -> None:
    links = [
        Link("https://api.test/items?page=2", {"rel": "next", "title": "Page 2, part two"}),
        Link("https://api.test/items?page=1", {"rel": "prev"}),
    ]
    assert parse(build(links)) == links


def test_round_trip_preserves_rel_list_and_hreflang() -> None:
    links = [Link("https://example.com/fr", {"rel": "start index", "hreflang": "fr"})]
    assert parse(build(links)) == links


def test_build_refuses_a_link_without_rel() -> None:
    with pytest.raises(LinkError, match="rel"):
        build([Link("https://a.test/", {"title": "x"})])


@pytest.mark.parametrize("value", ["a\r\nX-Evil: 1", "a\nb", "a\x00b", "a\x7fb", "caf\u00e9"])
def test_build_refuses_values_that_break_the_header(value: str) -> None:
    with pytest.raises(LinkError, match=r"title\*"):
        build([Link("https://a.test/", {"rel": "next", "title": value})])


def test_build_keeps_tabs_and_printable_ascii() -> None:
    value = "\t" + "".join(chr(c) for c in range(0x20, 0x7F))
    link = Link("https://a.test/", {"rel": "next", "title": value})
    assert parse(build([link]), strict=True) == [link]


@pytest.mark.parametrize("uri", ["https://a.test/a b", "https://a.test/\r\n", "caf\u00e9", "<x"])
def test_build_refuses_targets_that_are_not_uri_references(uri: str) -> None:
    with pytest.raises(LinkError, match="URI reference"):
        build([Link(uri, {"rel": "next"})])


def test_build_refuses_parameter_names_that_are_not_tokens() -> None:
    with pytest.raises(LinkError, match="token"):
        build([Link("https://a.test/", {"rel": "next", "bad name": "x"})])


def test_build_writes_star_values_bare_and_checks_them() -> None:
    title = encode_ext_value("nächstes Kapitel", "de")
    link = Link("/c4", {"rel": "next", "title*": title})
    assert build([link]) == "</c4>; rel=\"next\"; title*=UTF-8'de'n%C3%A4chstes%20Kapitel"
    assert parse(build([link]), strict=True)[0].title == "nächstes Kapitel"
    with pytest.raises(LinkError, match="ext-value"):
        build([Link("/c4", {"rel": "next", "title*": "nächstes"})])


def test_build_refuses_a_parameter_allowed_once_written_twice() -> None:
    with pytest.raises(LinkError, match="more than once"):
        build([Link("/", [("rel", "next"), ("title", "a"), ("title", "b")])])


def test_build_keeps_repeated_parameters_that_may_repeat() -> None:
    link = Link("/", [("rel", "alternate"), ("hreflang", "en"), ("hreflang", "fr")])
    assert build([link]) == '</>; rel="alternate"; hreflang="en"; hreflang="fr"'
    assert parse(build([link])) == [link]


def test_build_refuses_objects_that_are_not_links() -> None:
    with pytest.raises(TypeError, match="Link"):
        build(["<https://a.test/>; rel=next"])  # type: ignore[list-item]


def test_build_of_no_links_is_empty() -> None:
    assert build([]) == ""
