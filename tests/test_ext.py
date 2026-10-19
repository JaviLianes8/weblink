"""RFC 8187 extended values: decoding, encoding and the title* preference."""

from __future__ import annotations

import pytest

from weblinking import ExtValue, Link, LinkError, decode_ext_value, encode_ext_value, parse


def test_decode_keeps_the_language_and_names_the_charset() -> None:
    assert decode_ext_value("utf-8'en-GB'caf%C3%A9") == ExtValue("café", "en-GB", "UTF-8")


def test_charset_names_compare_case_insensitively() -> None:
    assert decode_ext_value("Utf-8''a").charset == "UTF-8"
    assert decode_ext_value("iso-8859-1''caf%E9") == ExtValue("café", "", "ISO-8859-1")


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("UTF-8", "form"),
        ("UTF-8'en", "form"),
        ("''abc", "charset"),
        ("UTF-16''abc", "charset"),
        ("UTF-8'e n'abc", "language"),
        ("UTF-8'-en'abc", "language"),
        ("UTF-8''a%2", "percent"),
        ("UTF-8''a%zz", "percent"),
        ("UTF-8''a b", "percent-encoded"),
        ("UTF-8''a'b", "percent-encoded"),
        ("UTF-8''%C3", "not valid UTF-8"),
        ("UTF-8''%FF", "not valid UTF-8"),
    ],
)
def test_decode_rejects_malformed_values(text: str, message: str) -> None:
    with pytest.raises(LinkError, match=message):
        decode_ext_value(text)


def test_encode_escapes_everything_outside_attr_char() -> None:
    assert encode_ext_value("nächstes Kapitel", "de") == "UTF-8'de'n%C3%A4chstes%20Kapitel"
    assert encode_ext_value("a*b'c%d") == "UTF-8''a%2Ab%27c%25d"
    assert encode_ext_value("!#$&+-.^_`|~") == "UTF-8''!#$&+-.^_`|~"


def test_encode_and_decode_round_trip() -> None:
    text = '€ 5, "quoted"; emoji \U0001f600'
    assert decode_ext_value(encode_ext_value(text, "en")) == ExtValue(text, "en", "UTF-8")


def test_encode_refuses_what_utf_8_cannot_carry() -> None:
    with pytest.raises(LinkError, match="surrogate"):
        encode_ext_value("\ud800")
    with pytest.raises(LinkError, match="language"):
        encode_ext_value("x", "e n")


def test_title_prefers_the_star_form_in_either_order() -> None:
    star = "title*=UTF-8''n%C3%A4chstes"
    for header in (f'</>; rel=next; title="plain"; {star}', f"</>; rel=next; {star}; title=x"):
        (link,) = parse(header)
        assert link.title == "nächstes"


def test_title_falls_back_when_the_star_form_is_broken() -> None:
    (link,) = parse('</>; rel=next; title*=garbage; title="plain"')
    assert link.title == "plain"
    assert link.params["title*"] == "garbage"


def test_get_reads_extension_star_parameters() -> None:
    link = Link("/", [("rel", "x"), ("example", "a"), ("example*", "UTF-8''%C3%A9")])
    assert link.get("example") == "é"
    assert link.get("EXAMPLE*") == "UTF-8''%C3%A9"
    assert link.get("missing") is None


def test_only_the_first_star_value_is_considered() -> None:
    link = Link("/", [("title*", "broken"), ("title*", "UTF-8''b"), ("title", "plain")])
    assert link.title == "plain"
