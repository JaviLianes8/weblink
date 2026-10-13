"""The Link value object: construction, equality, accessors, resolution and finding."""

from __future__ import annotations

import pickle

import pytest

from weblink import Link, LinkError, find, find_all, is_registered, parse


def test_names_are_lower_cased_and_pairs_keep_order() -> None:
    link = Link("/", [("REL", "next"), ("HrefLang", "en"), ("hreflang", "fr")])
    assert link.pairs == (("rel", "next"), ("hreflang", "en"), ("hreflang", "fr"))
    assert link.params == {"rel": "next", "hreflang": "en"}


def test_a_mapping_and_its_pairs_build_the_same_link() -> None:
    assert Link("/", {"rel": "next"}) == Link("/", [("rel", "next")])
    assert Link("/") == Link("/", {})


def test_links_are_immutable() -> None:
    link = Link("/", {"rel": "next"})
    with pytest.raises(AttributeError):
        link.uri = "/other"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        link.extra = 1  # type: ignore[attr-defined]
    link.params["rel"] = "changed"
    assert link.rel == "next"


def test_links_are_hashable_and_compare_by_value() -> None:
    a = Link("/a", {"rel": "next"})
    assert {a, Link("/a", {"rel": "next"})} == {a}
    assert a != Link("/a", {"rel": "prev"})
    assert a != Link("/b", {"rel": "next"})
    assert a != "/a"


def test_links_survive_pickling() -> None:
    link = Link("/a", [("rel", "next"), ("hreflang", "en"), ("hreflang", "fr")])
    assert pickle.loads(pickle.dumps(link)) == link


def test_the_repr_shows_a_dict_or_the_repeated_pairs() -> None:
    assert repr(Link("/a", {"rel": "next"})) == "Link('/a', {'rel': 'next'})"
    repeated = Link("/a", [("x", "1"), ("x", "2")])
    assert repr(repeated) == "Link('/a', [('x', '1'), ('x', '2')])"


def test_construction_checks_types() -> None:
    with pytest.raises(TypeError, match="uri"):
        Link(b"/a")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="str"):
        Link("/a", {"rel": 1})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="str"):
        Link("/a", [(1, "x")])  # type: ignore[list-item]


def test_accessors_read_their_parameters() -> None:
    (link,) = parse(
        '</a>; rel="next"; rev=made; anchor="#s"; type="text/html"; media="print"; hreflang=fr'
    )
    assert (link.rel, link.rev, link.anchor) == ("next", "made", "#s")
    assert (link.type, link.media, link.hreflang) == ("text/html", "print", "fr")
    empty = Link("/a")
    assert (empty.rel, empty.rev, empty.anchor, empty.title) == (None, None, None, None)
    assert (empty.type, empty.media, empty.hreflang) == (None, None, None)
    assert empty.rels == () and empty.hreflangs == ()


def test_relation_types_compare_case_insensitively() -> None:
    # RFC 8288 sections 2.1.1 and 2.1.2: registered names and extension URIs alike.
    (link,) = parse('</a>; rel="Next PREV https://Example.net/Rel"')
    assert link.rel == "Next PREV https://Example.net/Rel"
    assert link.rels == ("next", "prev", "https://example.net/rel")
    assert link.has_rel("NEXT") and link.has_rel("prev")
    assert link.has_rel("https://example.net/rel") and link.has_rel("HTTPS://EXAMPLE.NET/REL")


def test_only_ascii_letters_fold() -> None:
    (link,) = parse('</a>; rel="bookmark"')
    assert not link.has_rel("bookmar\u212a")
    assert not is_registered("bookmar\u212a")


def test_find_picks_links_by_relation_type() -> None:
    links = parse('</1>; rel="next", </2>; rel="Last next", </3>; rel=prev')
    found = find(links, "next")
    assert found is not None and found.uri == "/1"
    assert [link.uri for link in find_all(links, "NEXT")] == ["/1", "/2"]
    assert find(links, "first") is None and find_all(links, "first") == []


def test_is_registered_reads_the_iana_names() -> None:
    assert is_registered("next") and is_registered("Next") and is_registered("openid2.local_id")
    assert not is_registered("nxt") and not is_registered("https://example.net/rel")


def test_resolve_resolves_the_target_and_the_anchor() -> None:
    link = Link("../g", [("rel", "next"), ("anchor", "#frag"), ("title", "../x")])
    resolved = link.resolve("http://a/b/c/d")
    assert resolved == Link(
        "http://a/b/g", [("rel", "next"), ("anchor", "http://a/b/c/d#frag"), ("title", "../x")]
    )


def test_context_is_the_anchor_or_the_base() -> None:
    assert Link("/x", {"rel": "next"}).context("http://a/b") == "http://a/b"
    assert Link("/x", {"anchor": "#s"}).context("http://a/b") == "http://a/b#s"
    assert Link("/x", {"anchor": "http://o/"}).context("http://a/b") == "http://o/"


def test_resolution_refuses_a_relative_base() -> None:
    with pytest.raises(LinkError):
        Link("g", {"rel": "next"}).resolve("/b")
