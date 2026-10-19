"""Contracts for the findings of the first round of independent QA on 1.0.0."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from weblinking import Link, LinkError, build, find, find_all, parse, resolve_uri

SRC = Path(__file__).resolve().parents[1] / "src"
SECRET = "hunter2-S3CRET"


def test_attributes_cannot_be_deleted_or_assigned() -> None:
    link = Link("/b", {"rel": "up"})
    for name in ("_uri", "_pairs", "uri", "extra"):
        with pytest.raises(AttributeError, match="immutable"):
            delattr(link, name)
        with pytest.raises(AttributeError, match="immutable"):
            setattr(link, name, "/evil")
    assert link == Link("/b", {"rel": "up"})
    assert hash(link) == hash(Link("/b", {"rel": "up"}))


@pytest.mark.parametrize(
    ("name", "stored", "ascii"),
    [
        ("\u212aind", "\u212aind", "kind"),
        ("\u0130D", "\u0130d", "id"),
        ("\u017fIZE", "\u017fize", "size"),
    ],
)
def test_parameter_names_fold_only_ascii_letters(name: str, stored: str, ascii: str) -> None:
    link = Link("/a", [("rel", "next"), (name, "v")])
    assert link.pairs[1][0] == stored
    assert link.get(name) == "v" and link.get_all(stored) == ["v"]
    assert link.get(ascii) is None and link.get_all(ascii.upper()) == []
    assert parse(f"</a>; rel=next; {name}=v")[0].get(ascii) is None
    with pytest.raises(LinkError, match="not a token"):
        build([link])


def test_ascii_parameter_names_still_fold() -> None:
    link = Link("/a", [("REL", "next"), ("HrefLang", "en")])
    assert link.pairs == (("rel", "next"), ("hreflang", "en"))
    assert link.get_all("HREFLANG") == ["en"]


@pytest.mark.parametrize("space", ["\xa0", "\x85", "\x0b", "\x0c", "\x1c", "\u2003", "\u3000"])
def test_relation_types_split_only_on_spaces_and_tabs(space: str) -> None:
    links = parse(f'</a>; rel="next{space}evil"')
    assert links[0].rels == (f"next{space}evil",)
    assert not links[0].has_rel("next")
    assert find(links, "next") is None
    assert find_all(links, "evil") == []


def test_relation_types_split_on_runs_of_whitespace_the_parser_skips() -> None:
    assert Link("/a", {"rel": " Next\t\tlast \r\n up "}).rels == ("next", "last", "up")


@pytest.mark.parametrize(
    "call",
    [
        lambda: parse(
            f'<https://alice:{SECRET}@api.example/items?page=2 >; rel="next"', strict=True
        ),
        lambda: build([Link(f"https://alice:{SECRET}@h/ x", {"rel": "next"})]),
        lambda: build([Link("/a", {"rel": "next", "anchor": f"/x y?access_token={SECRET}"})]),
        lambda: parse(f'</a>; rel=next; anchor="//h/ ?sig={SECRET}"', strict=True),
        lambda: resolve_uri("a", f"//h/?access_token={SECRET}"),
        lambda: Link("/a", {"rel": "up"}).context(f"//u:{SECRET}@h/"),
    ],
)
def test_error_messages_never_quote_credentials_or_queries(call: object) -> None:
    with pytest.raises(LinkError) as caught:
        call()  # type: ignore[operator]
    assert SECRET not in str(caught.value)
    assert "***" in str(caught.value)


def test_redacted_messages_keep_the_rest_of_the_value() -> None:
    with pytest.raises(LinkError, match=r"'https://\*\*\*@h/ x' is not a URI reference"):
        build([Link("https://user:pw@h/ x", {"rel": "next"})])
    with pytest.raises(LinkError, match=r"'//h/\?\*\*\*' is not an absolute URI"):
        resolve_uri("a", "//h/?token=1")
    with pytest.raises(LinkError, match=r"'nope\?' is not an absolute URI"):
        resolve_uri("a", "nope?")


class _LyingFind(str):
    def find(self, *args: object, **kwargs: object) -> int:
        return 0


class _LyingLen(str):
    def __len__(self) -> int:
        return 10**9


def test_parse_reads_str_subclasses_as_plain_text() -> None:
    expected = [Link("/a", {"rel": "x"}), Link("/b", {"rel": "y"})]
    assert parse(_LyingFind("</a>; rel=x, junk, </b>; rel=y")) == expected
    assert parse([_LyingFind("</a>; rel=x, junk, </b>; rel=y")]) == expected
    assert parse(_LyingLen("</a>; rel=x")) == expected[:1]


def test_the_command_exits_quietly_when_the_reader_stops_early(tmp_path: Path) -> None:
    source = tmp_path / "big.txt"
    source.write_text(", ".join(f"</p{i}>; rel=next" for i in range(40_000)), encoding="ascii")
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    with source.open("rb") as stdin:
        child = subprocess.Popen(
            [sys.executable, "-m", "weblinking"],
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        assert child.stdout is not None and child.stderr is not None
        assert child.stdout.read(50).startswith(b"[")
        child.stdout.close()
        errors = child.stderr.read()
        status = child.wait(timeout=120)
    assert errors == b""
    assert status == 1


def test_a_valueless_parameter_ends_at_a_comma() -> None:
    expected = [Link("/a", {"foo": ""}), Link("/b", {"rel": "x"})]
    assert parse("</a>; foo, </b>; rel=x") == expected
    strict = parse("</a>; rel=x; foo, </b>; rel=y", strict=True)
    assert strict == [Link("/a", {"rel": "x", "foo": ""}), Link("/b", {"rel": "y"})]


def test_strict_refuses_an_unclosed_quote_ending_in_a_backslash() -> None:
    with pytest.raises(LinkError, match="unclosed quoted string") as caught:
        parse('</a>; rel="x\\', strict=True)
    assert caught.value.position == 10
    assert parse('</a>; rel="x\\') == [Link("/a", {"rel": "x"})]


def test_equality_and_hash_follow_pair_order_and_repetition() -> None:
    a = Link("/a", [("rel", "x"), ("a", "1")])
    swapped = Link("/a", [("a", "1"), ("rel", "x")])
    repeated = Link("/a", [("rel", "x"), ("a", "1"), ("a", "1")])
    assert a != swapped and a != repeated
    assert len({hash(a), hash(swapped), hash(repeated)}) == 3


def test_the_first_anchor_is_the_context() -> None:
    link = Link("/b", [("rel", "up"), ("anchor", "#one"), ("anchor", "#two")])
    assert link.anchor == "#one"
    assert link.context("http://a.test/c") == "http://a.test/c#one"


def test_a_starred_rel_never_overrides_rel() -> None:
    link = Link("/b", [("rel", "next"), ("rel*", "UTF-8''prev")])
    assert (link.rel, link.rels, link.has_rel("next")) == ("next", ("next",), True)
    assert not link.has_rel("prev")
    assert find([link], "next") is link and find([link], "prev") is None
