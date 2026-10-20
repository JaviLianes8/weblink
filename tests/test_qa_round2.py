"""Contracts for the findings of the second round of independent QA on 1.0.0."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from weblinking import Link, LinkError, build, parse, resolve_uri

SECRET = "hunter2SECRET"


@pytest.mark.parametrize(
    ("call", "shown"),
    [
        (
            lambda: parse(f"<https://alice:{SECRET}#x@h/ p>; rel=next", strict=True),
            "'https://***'",
        ),
        (
            lambda: parse(f"<https://alice:{SECRET}?x@h/ p>; rel=next", strict=True),
            "'https://***'",
        ),
        (
            lambda: parse(f"<https://alice:pa/{SECRET}@h/ p>; rel=next", strict=True),
            "'https://***@h/ p'",
        ),
        (lambda: resolve_uri("a", f"https//alice:{SECRET}@h/"), "'***@h/'"),
        (lambda: build([Link(f"alice:{SECRET}@h/ p", {"rel": "next"})]), "'***@h/ p'"),
    ],
)
def test_userinfo_stays_hidden_whatever_the_value_looks_like(
    call: Callable[[], object], shown: str
) -> None:
    with pytest.raises(LinkError) as caught:
        call()
    assert SECRET not in str(caught.value)
    assert "alice" not in str(caught.value)
    assert shown in str(caught.value)


@pytest.mark.parametrize(
    "call",
    [
        lambda: build(
            [Link("/a", {"rel": "x", "anchor": f"https://h/cb y#access_token={SECRET}"})]
        ),
        lambda: parse(f"<https://h/cb y#access_token={SECRET}>; rel=next", strict=True),
    ],
)
def test_fragments_are_hidden_like_queries(call: Callable[[], object]) -> None:
    with pytest.raises(LinkError) as caught:
        call()
    assert SECRET not in str(caught.value)
    assert "'https://h/cb y#***'" in str(caught.value)


def test_redacted_fragments_keep_their_mark() -> None:
    with pytest.raises(LinkError, match=r"base '//h/#\*\*\*' is not an absolute URI"):
        resolve_uri("a", "//h/#frag")
    with pytest.raises(LinkError, match=r"target '/x y#\*\*\*' is not a URI reference"):
        build([Link("/x y#frag", {"rel": "next"})])
    with pytest.raises(LinkError, match=r"base 'nope#' is not an absolute URI"):
        resolve_uri("a", "nope#")


class _LyingPair(tuple):  # type: ignore[type-arg]
    def __len__(self) -> int:
        return 2


class _LyingList(list):  # type: ignore[type-arg]
    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: object) -> object:  # type: ignore[override]
        return "x"


def test_pairs_are_read_without_their_subclass_methods() -> None:
    with pytest.raises(TypeError, match="pair"):
        Link("/a", [_LyingPair(("a",))])
    with pytest.raises(TypeError, match="pair"):
        Link("/a", [_LyingList(["a", "b", "c"])])
    assert Link("/a", [_LyingList(["rel", "x"])]).pairs == (("rel", "x"),)


def test_get_and_title_return_the_first_of_repeated_plain_values() -> None:
    link = Link("/a", [("rel", "x"), ("type", "a/b"), ("type", "c/d")])
    assert link.get("type") == "a/b"
    assert Link("/a", [("rel", "x"), ("title", "A"), ("title", "B")]).title == "A"


def test_rev_returns_the_first_rev() -> None:
    assert Link("/a", [("rel", "x"), ("rev", "made"), ("rev", "other")]).rev == "made"


@pytest.mark.parametrize(
    ("name", "plain", "starred"),
    [
        ("media", "print", "screen"),
        ("type", "text/html", "html"),
        ("rev", "made", "other"),
        ("hreflang", "fr", "de"),
    ],
)
def test_raw_attributes_ignore_a_starred_twin(name: str, plain: str, starred: str) -> None:
    link = Link("/a", [("rel", "x"), (name, plain), (name + "*", f"UTF-8''{starred}")])
    assert getattr(link, name) == plain
    assert link.get(name) == starred
