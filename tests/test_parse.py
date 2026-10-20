import pytest

from weblinking import Link, parse


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


def test_several_header_lines_are_read_in_order() -> None:
    links = parse(['<https://a.test/1>; rel="next"', '<https://a.test/2>; rel="last"'])
    assert [link.uri for link in links] == ["https://a.test/1", "https://a.test/2"]


def test_a_quote_never_continues_into_the_next_line() -> None:
    links = parse(['<https://a.test/1>; title="open', '<https://a.test/2>; rel="last"'])
    assert [link.uri for link in links] == ["https://a.test/1", "https://a.test/2"]


def test_bytes_are_refused_with_a_clear_message() -> None:
    with pytest.raises(TypeError, match="bytes"):
        parse(b'<https://a.test/>; rel="next"')  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="lines must be str"):
        parse([b"<https://a.test/>"])  # type: ignore[list-item]


def test_an_unquoted_value_runs_to_the_next_semicolon() -> None:
    # RFC 8288 Appendix B.3 step 7.4: a bare value ends at ";" or ",", not at a space.
    (link,) = parse("<https://a.test/>; rel=next prev ; type=text/html")
    assert link.rels == ("next", "prev")
    assert link.type == "text/html"


def test_repeated_hreflang_values_are_all_kept() -> None:
    (link,) = parse('<https://a.test/>; rel="alternate"; hreflang=en; hreflang=fr')
    assert link.hreflang == "en"
    assert link.hreflangs == ("en", "fr")
    assert link.pairs == (("rel", "alternate"), ("hreflang", "en"), ("hreflang", "fr"))


def test_a_parameter_without_a_value_is_empty() -> None:
    (link,) = parse("<https://a.test/>; rel=next; crossorigin")
    assert link.params == {"rel": "next", "crossorigin": ""}


def test_empty_parameter_names_are_dropped() -> None:
    (link,) = parse("<https://a.test/>; ; =x; rel=next")
    assert link.pairs == (("rel", "next"),)


def test_whitespace_around_the_equals_sign_is_allowed() -> None:
    (link,) = parse('<https://a.test/> ; rel = "next" ; title =x')
    assert link.params == {"rel": "next", "title": "x"}


def test_junk_after_a_value_keeps_the_link_and_the_next_one() -> None:
    links = parse('<https://a.test/1>; rel="next" junk; x=1, <https://a.test/2>; rel="last"')
    assert links == [
        Link("https://a.test/1", {"rel": "next"}),
        Link("https://a.test/2", {"rel": "last"}),
    ]


def test_an_unclosed_quote_in_junk_does_not_hide_the_next_link() -> None:
    links = parse('junk"here, <https://a.test/2>; rel="last"')
    assert links == [Link("https://a.test/2", {"rel": "last"})]


def test_an_unclosed_bracket_in_junk_does_not_hide_the_next_link() -> None:
    links = parse('junk<here, <https://a.test/2>; rel="last"')
    assert links == [Link("https://a.test/2", {"rel": "last"})]


def test_junk_with_a_quoted_comma_still_reaches_the_next_link() -> None:
    links = parse('junk "a, b" more, <https://a.test/2>; rel="last"')
    assert links == [Link("https://a.test/2", {"rel": "last"})]


def test_a_comma_inside_the_target_does_not_split() -> None:
    (link,) = parse("<https://a.test/a,b>; rel=next")
    assert link.uri == "https://a.test/a,b"


def test_a_backslash_at_the_end_of_an_unclosed_quote_is_dropped() -> None:
    (link,) = parse('<https://a.test/>; title="abc\\')
    assert link.title == "abc"


def test_folded_lines_and_tabs_are_tolerated() -> None:
    (link,) = parse('<https://a.test/>;\r\n\trel="next";\ttitle="t"')
    assert link.params == {"rel": "next", "title": "t"}
