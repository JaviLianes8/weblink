"""Strict parsing: what RFC 8288 rejects raises LinkError with the offset in the line."""

from __future__ import annotations

import pytest

from weblink import Link, LinkError, parse


def _offset(header: str) -> int | None:
    with pytest.raises(LinkError) as caught:
        parse(header, strict=True)
    return caught.value.position


def test_a_valid_header_parses_as_in_lenient_mode() -> None:
    header = '<https://a.test/2>; rel="next"; title="Two", <https://a.test/9>;rel=last'
    assert parse(header, strict=True) == parse(header)


def test_empty_list_elements_are_allowed() -> None:
    assert parse(" , <https://a.test/>; rel=next ,, ", strict=True) == [
        Link("https://a.test/", {"rel": "next"})
    ]


def test_text_that_is_not_a_link_is_rejected_where_it_starts() -> None:
    assert _offset("<https://a.test/>; rel=next, junk") == 29


def test_an_unclosed_bracket_is_rejected() -> None:
    assert _offset("<https://a.test/; rel=next") == 0


def test_junk_after_a_parameter_is_rejected() -> None:
    assert _offset('<https://a.test/>; rel="next" junk') == 30


def test_a_missing_parameter_name_is_rejected() -> None:
    assert _offset("<https://a.test/>; rel=next;") == 28
    assert _offset("<https://a.test/>; rel=next; =x") == 29


def test_a_name_that_is_not_a_token_is_rejected() -> None:
    assert _offset('<https://a.test/>; rel=next; ti"tle=x') == 29


def test_a_bare_value_must_be_a_token() -> None:
    assert _offset("<https://a.test/>; rel=next; title=two words") == 35
    assert _offset("<https://a.test/>; rel=next; title=") == 35


def test_an_unclosed_quote_is_rejected_where_it_opens() -> None:
    assert _offset('<https://a.test/>; rel=next; title="open') == 35


def test_control_characters_in_a_quoted_string_are_rejected() -> None:
    assert _offset('<https://a.test/>; rel=next; title="a\x01b"') == 37


def test_a_quoted_pair_must_escape_a_visible_character() -> None:
    assert _offset('<https://a.test/>; rel=next; title="a\\\x7fb"') == 38


def test_line_breaks_are_not_whitespace_in_strict_mode() -> None:
    assert _offset("<https://a.test/>;\r\n rel=next") == 18


def test_a_target_that_is_not_a_uri_reference_is_rejected() -> None:
    assert _offset("<https://a.test/a b>; rel=next") == 0
    assert _offset("<https://a.test/%zz>; rel=next") == 0
    assert _offset("<https://a.test/café>; rel=next") == 0


def test_rel_is_required() -> None:
    with pytest.raises(LinkError, match="rel"):
        parse('<https://a.test/>; title="x"', strict=True)


@pytest.mark.parametrize("name", ["rel", "media", "title", "title*", "type"])
def test_parameters_allowed_once_are_rejected_twice(name: str) -> None:
    value = "UTF-8''x" if name.endswith("*") else "x"
    header = f"<https://a.test/>; rel=next; {name}={value}; {name}={value}"
    if name == "rel":
        header = "<https://a.test/>; rel=next; rel=prev"
    with pytest.raises(LinkError, match="more than once"):
        parse(header, strict=True)


def test_hreflang_and_extensions_may_repeat() -> None:
    header = "<https://a.test/>; rel=alternate; hreflang=en; hreflang=fr; x=1; x=2"
    (link,) = parse(header, strict=True)
    assert link.hreflangs == ("en", "fr")


def test_the_error_of_a_later_link_points_at_that_link() -> None:
    assert _offset("<https://a.test/1>; rel=next, <https://a.test/2>; title=x") == 30


@pytest.mark.parametrize("rel", ['" next"', '"next "', '""', "next_page", '"http//x"', '"1abc"'])
def test_malformed_relation_types_are_rejected(rel: str) -> None:
    with pytest.raises(LinkError):
        parse(f"<https://a.test/>; rel={rel}", strict=True)


@pytest.mark.parametrize(
    "rel", ['"next prev"', '"next  prev"', "Next", '"https://example.net/rel/x"', "a.b-c"]
)
def test_valid_relation_types_are_accepted(rel: str) -> None:
    assert parse(f"<https://a.test/>; rel={rel}", strict=True)


def test_rev_follows_the_relation_type_grammar() -> None:
    assert parse("<https://a.test/>; rel=next; rev=made", strict=True)
    with pytest.raises(LinkError):
        parse('<https://a.test/>; rel=next; rev="bad value!"', strict=True)


def test_an_anchor_must_be_a_uri_reference() -> None:
    assert parse('<https://a.test/>; rel=next; anchor="#foo"', strict=True)
    with pytest.raises(LinkError, match="anchor"):
        parse('<https://a.test/>; rel=next; anchor="a b"', strict=True)


def test_a_star_value_must_decode() -> None:
    with pytest.raises(LinkError, match="ext-value"):
        parse("<https://a.test/>; rel=next; title*=nonsense", strict=True)


def test_a_star_value_must_not_be_quoted() -> None:
    assert _offset("<https://a.test/>; rel=next; title*=\"UTF-8''x\"") == 36
    (link,) = parse("<https://a.test/>; rel=next; title*=\"UTF-8''x\"")
    assert link.title == "x"


def test_an_error_message_carries_the_offset() -> None:
    with pytest.raises(LinkError, match=r"\(offset 0\)") as caught:
        parse("junk", strict=True)
    assert caught.value.message == "expected '<' to start a link"
