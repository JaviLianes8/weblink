"""RFC 3986 resolution beyond the RFC table (that table is in test_sources.py).

The cases here are hand-written from the section 5.2 algorithm.
"""

from __future__ import annotations

import pytest

from weblinking import LinkError, resolve_uri


def test_a_base_without_a_scheme_is_refused() -> None:
    for base in ("/relative/base", "//host/path", "", "1http://a/", "ht tp://a/"):
        with pytest.raises(LinkError, match="absolute"):
            resolve_uri("g", base)


def test_an_empty_base_path_with_an_authority_gets_a_slash() -> None:
    assert resolve_uri("g", "http://a") == "http://a/g"
    assert resolve_uri("g", "http://a?q") == "http://a/g"


def test_a_base_without_an_authority_merges_its_path() -> None:
    assert resolve_uri("c", "urn:a/b") == "urn:a/c"
    assert resolve_uri("c", "mailto:x") == "mailto:c"


def test_the_base_fragment_is_never_inherited() -> None:
    assert resolve_uri("", "http://a/b#frag") == "http://a/b"
    assert resolve_uri("?y", "http://a/b#frag") == "http://a/b?y"


def test_an_empty_query_and_fragment_are_kept() -> None:
    assert resolve_uri("g?#", "http://a/b") == "http://a/g?#"


def test_an_absolute_reference_loses_its_dot_segments() -> None:
    assert resolve_uri("https://x/a/./b/../c", "http://a/") == "https://x/a/c"
    assert resolve_uri("//x/a/../b", "http://a/") == "http://x/b"


def test_dot_segments_at_the_root_stop_there() -> None:
    assert resolve_uri("../../../..", "http://a/b/c") == "http://a/"
    assert resolve_uri("/..", "http://a/b") == "http://a/"
    assert resolve_uri("/.", "http://a/b") == "http://a/"


def test_a_bare_dot_or_dot_dot_path_is_removed() -> None:
    # Only a reference with a scheme keeps its path unmerged, so "." and ".." stay bare.
    assert resolve_uri("g:..", "http://a/b") == "g:"
    assert resolve_uri("g:.", "http://a/b") == "g:"
