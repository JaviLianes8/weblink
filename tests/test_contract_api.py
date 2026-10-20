"""The 1.0.0 surface: signatures, wrong-type arguments, plain values, bounded messages."""

from __future__ import annotations

import inspect
import pickle
from collections.abc import Callable
from typing import Any

import pytest

import weblinking
from weblinking import (
    ExtValue,
    Link,
    LinkError,
    build,
    decode_ext_value,
    encode_ext_value,
    parse,
    resolve_uri,
)

# The parameter names, kinds and defaults are part of the promise (callers use keywords).
SIGNATURES = {
    "build": "(links: 'Iterable[Link]') -> 'str'",
    "decode_ext_value": "(text: 'str') -> 'ExtValue'",
    "encode_ext_value": "(value: 'str', language: 'str' = '') -> 'str'",
    "find": "(links: 'Iterable[Link]', relation_type: 'str') -> 'Link | None'",
    "find_all": "(links: 'Iterable[Link]', relation_type: 'str') -> 'list[Link]'",
    "is_registered": "(relation_type: 'str') -> 'bool'",
    "parse": "(header: 'str | Iterable[str]', *, strict: 'bool' = False) -> 'list[Link]'",
    "resolve_uri": "(reference: 'str', base: 'str') -> 'str'",
    "Link": "(uri: 'str', params: 'Params' = ()) -> 'None'",
    "LinkError": "(message: 'str', position: 'int | None' = None) -> 'None'",
}
LINK_MEMBERS = {
    *("uri", "pairs", "params", "get_all", "get", "rel", "rels", "has_rel", "rev", "anchor"),
    *("title", "type", "media", "hreflang", "hreflangs", "resolve", "context"),
}
HUGE = "x" * 200_000
LINK = Link("/a", {"rel": "next"})
# Misuse goes through untyped handles: type checkers rightly reject these calls.
W: Any = weblinking
UNTYPED_LINK: Any = LINK


@pytest.mark.parametrize("name", sorted(SIGNATURES))
def test_signatures_are_pinned(name: str) -> None:
    obj = getattr(weblinking, name)
    target = obj.__init__ if inspect.isclass(obj) else obj
    shown = str(inspect.signature(target)).replace("(self, ", "(")
    assert shown == SIGNATURES[name]


def test_link_members_and_ext_value_fields_are_pinned() -> None:
    public = {name for name in dir(Link) if not name.startswith("_")}
    assert public == LINK_MEMBERS
    assert ExtValue._fields == ("value", "language", "charset")
    assert issubclass(LinkError, ValueError)
    assert isinstance(weblinking.REGISTERED_RELATIONS, frozenset)


@pytest.mark.parametrize(
    "call",
    [
        lambda: W.resolve_uri(1, "http://a/"),
        lambda: W.resolve_uri("a", 1),
        lambda: W.find([LINK], 1),
        lambda: W.find_all([LINK], b"next"),
        lambda: W.find(["</a>; rel=next"], "next"),
        lambda: W.find_all([None], "next"),
        lambda: W.is_registered(1),
        lambda: W.encode_ext_value(1),
        lambda: W.encode_ext_value("a", 1),
        lambda: W.decode_ext_value(b"UTF-8''a"),
        lambda: UNTYPED_LINK.get(1),
        lambda: UNTYPED_LINK.get_all(None),
        lambda: UNTYPED_LINK.has_rel(1),
        lambda: UNTYPED_LINK.resolve(1),
        lambda: UNTYPED_LINK.context(1),
        lambda: W.Link("a", "rel"),
        lambda: W.Link("a", b"rel"),
        lambda: W.Link("a", [("rel", "next", "x")]),
        lambda: W.Link("a", ["ab"]),
        lambda: W.Link("a", 5),
        lambda: W.build(LINK),
        lambda: W.build("</a>"),
        lambda: W.build([LINK, "</a>"]),
        lambda: W.parse(b"</a>"),
        lambda: W.parse([b"</a>"]),
    ],
)
def test_wrong_argument_types_raise_type_error(call: Callable[[], object]) -> None:
    with pytest.raises(TypeError):
        call()


def test_lists_are_accepted_as_pairs() -> None:
    assert Link("/a", [["rel", "next"]]) == Link("/a", {"rel": "next"})


def test_str_subclasses_are_stored_as_plain_str() -> None:
    class Text(str):
        pass

    link = Link(Text("/a"), [(Text("Rel"), Text("next"))])
    assert type(link.uri) is str
    assert all(type(part) is str for pair in link.pairs for part in pair)
    assert type(resolve_uri(Text("b"), Text("http://a/"))) is str


@pytest.mark.parametrize(
    "call",
    [
        lambda: decode_ext_value(HUGE),
        lambda: decode_ext_value("UTF-8''" + HUGE + "%"),
        lambda: decode_ext_value("UTF-8''" + HUGE + " "),
        lambda: decode_ext_value(HUGE + "''a"),
        lambda: decode_ext_value("UTF-8'" + HUGE + "!'a"),
        lambda: encode_ext_value("a", HUGE + "!"),
        lambda: build([Link(" " + HUGE, {"rel": "next"})]),
        lambda: build([Link("/a", {"rel": "next", "anchor": " " + HUGE})]),
        lambda: build([Link("/a", {"rel": "next " + HUGE + "!"})]),
        lambda: build([Link("/a", {"rel": " " + HUGE})]),
        lambda: build([Link("/a", {"rel": "next", HUGE + " ": "v"})]),
        lambda: build([Link("/a", {"rel": "next", HUGE: "\n"})]),
        lambda: parse("<" + HUGE + " >; rel=next", strict=True),
        lambda: resolve_uri("a", HUGE),
        lambda: LINK.context(HUGE),
    ],
)
def test_error_messages_quote_at_most_eighty_characters(call: Callable[[], object]) -> None:
    with pytest.raises(LinkError) as caught:
        call()
    assert len(str(caught.value)) < 300
    assert "x" * 81 not in str(caught.value)


def test_a_short_value_is_quoted_whole() -> None:
    with pytest.raises(LinkError, match="'nope' is not an absolute URI"):
        resolve_uri("a", "nope")
    with pytest.raises(LinkError, match=r"'x{80}' is not an absolute URI"):
        resolve_uri("a", "x" * 80)
    with pytest.raises(LinkError, match=r"'x{80}'\.\.\. \(81 characters\)"):
        resolve_uri("a", "x" * 81)


def test_context_refuses_a_relative_base_with_or_without_an_anchor() -> None:
    for link in (LINK, Link("/a", {"rel": "next", "anchor": "#x"})):
        with pytest.raises(LinkError, match="absolute"):
            link.context("/relative")
    assert LINK.context("http://a/b#f") == "http://a/b#f"


def test_errors_and_links_pickle_under_the_public_module() -> None:
    error = pickle.loads(pickle.dumps(LinkError("bad", 4)))
    assert (error.message, error.position, str(error)) == ("bad", 4, "bad (offset 4)")
    assert b"weblinking._" not in pickle.dumps(LINK)
    assert b"weblinking._" not in pickle.dumps(ExtValue("a", "", "UTF-8"))
    assert b"weblinking._" not in pickle.dumps(LinkError("bad"))


def test_a_value_error_handler_catches_every_link_error() -> None:
    with pytest.raises(ValueError, match="offset 0"):
        parse("junk", strict=True)
    with pytest.raises(LinkError) as caught:
        decode_ext_value("UTF-8''%ZZ")
    assert caught.value.position is None
