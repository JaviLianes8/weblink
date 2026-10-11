from weblink import Link, parse


def test_single_link_with_rel() -> None:
    links = parse('<https://example.com/next>; rel="next"')
    assert links == [Link("https://example.com/next", {"rel": "next"})]


def test_link_without_quotes_on_value() -> None:
    links = parse("<https://example.com/>; rel=next")
    assert links == [Link("https://example.com/", {"rel": "next"})]


def test_multiple_links_for_pagination() -> None:
    header = (
        '<https://api.test/items?page=2>; rel="next", <https://api.test/items?page=1>; rel="prev"'
    )
    links = parse(header)
    assert [link.uri for link in links] == [
        "https://api.test/items?page=2",
        "https://api.test/items?page=1",
    ]
    assert [link.rel for link in links] == ["next", "prev"]


def test_quoted_title_may_contain_a_comma() -> None:
    links = parse('<https://example.com/a>; rel="next"; title="Page 2, the sequel"')
    assert len(links) == 1
    assert links[0].title == "Page 2, the sequel"


def test_comma_inside_title_does_not_split_links() -> None:
    header = '<https://a.test/1>; title="one, two", <https://a.test/2>; rel="next"'
    links = parse(header)
    assert len(links) == 2
    assert links[0].title == "one, two"
    assert links[1].rel == "next"


def test_rel_with_multiple_space_separated_values() -> None:
    links = parse('<https://example.com/>; rel="start index"')
    assert links[0].rel == "start index"
    assert links[0].rels == ("start", "index")


def test_type_and_hreflang_parameters() -> None:
    links = parse('<https://example.com/fr>; rel="alternate"; type="text/html"; hreflang="fr"')
    assert links[0].type == "text/html"
    assert links[0].hreflang == "fr"


def test_parameter_names_are_lowercased() -> None:
    links = parse('<https://example.com/>; REL="next"')
    assert links[0].rel == "next"


def test_first_occurrence_of_a_parameter_wins() -> None:
    links = parse('<https://example.com/>; rel="next"; rel="prev"')
    assert links[0].rel == "next"


def test_escaped_quote_inside_a_quoted_value() -> None:
    links = parse('<https://example.com/>; title="a \\"quoted\\" word"')
    assert links[0].title == 'a "quoted" word'


def test_empty_header_yields_no_links() -> None:
    assert parse("") == []
    assert parse("   ") == []


def test_malformed_segments_are_skipped() -> None:
    header = 'not-a-link; rel="next", <https://example.com/ok>; rel="next"'
    links = parse(header)
    assert links == [Link("https://example.com/ok", {"rel": "next"})]


def test_unterminated_uri_does_not_crash() -> None:
    assert parse("<https://example.com/no-close; rel=next") == []


def test_unterminated_quote_does_not_crash() -> None:
    links = parse('<https://example.com/>; title="unterminated')
    assert links[0].title == "unterminated"
