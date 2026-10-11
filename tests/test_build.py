import pytest

from weblink import Link, LinkError, build, parse


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
    result = build([Link("https://a.test/", {"title": 'a "quote"'})])
    assert result == '<https://a.test/>; title="a \\"quote\\""'


def test_build_rejects_an_empty_uri() -> None:
    with pytest.raises(LinkError):
        build([Link("", {"rel": "next"})])


def test_round_trip_through_parse() -> None:
    links = [
        Link("https://api.test/items?page=2", {"rel": "next", "title": "Page 2, part two"}),
        Link("https://api.test/items?page=1", {"rel": "prev"}),
    ]
    assert parse(build(links)) == links


def test_round_trip_preserves_rel_list_and_hreflang() -> None:
    links = [Link("https://example.com/fr", {"rel": "start index", "hreflang": "fr"})]
    assert parse(build(links)) == links
