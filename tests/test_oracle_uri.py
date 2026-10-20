"""Reference resolution against two oracles: RFC 3986 section 5.2 written out step by
step (`uri_oracle.py`) and the rfc3986 package.

`pip install rfc3986==2.0.0` enables the second; it is skipped when missing. That
package departs from the RFC text in four places, which the test names and asserts.
"""

from __future__ import annotations

import importlib.metadata
import random
import re

import pytest
import uri_oracle

from weblinking import resolve_uri

VALID_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*")
PIECES = ["a", "b", "g", ".", "..", "/", "/", "/", "?", "#", ";", "=", "x:y", "@", "!", "%41"]
LEADS = ["", "", "/", "//h", "//", "http:", "s:", "?", "#", "./", "../"]
BASES = ["http://a", "http://a/", "s:", "s:/", "s:p", "http://a/b/c/d;p?q", "file:///x/y"]
BASES += ["urn:a:b", "http://u@h:1/p/q?r#f", "s://"]


def _reference(rng: random.Random) -> str:
    return rng.choice(LEADS) + "".join(rng.choice(PIECES) for _ in range(rng.randint(0, 8)))


@pytest.mark.parametrize("seed", [3986, 8288])
def test_resolution_matches_the_rfc_pseudocode(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(100_000):
        reference = _reference(rng)
        base = rng.choice(BASES) + "".join(rng.choice(PIECES) for _ in range(rng.randint(0, 4)))
        if "#" in base.partition("#")[2] or base.startswith(("?", "#", "/")):
            continue
        scheme = uri_oracle.split(reference)[0]
        if scheme is not None and not VALID_SCHEME.fullmatch(scheme):
            continue  # not a URI reference: covered by the test below
        assert resolve_uri(reference, base) == uri_oracle.resolve(reference, base)


def _rfc3986_departure(reference: str, ours: str) -> str | None:
    """Which documented difference of rfc3986 2.0.0 explains a mismatch, if any."""
    _, authority, path, _, _ = uri_oracle.split(ours)
    if authority == "":
        return "it drops an empty authority (RFC 3986 section 5.3 keeps it)"
    r_scheme, r_authority = uri_oracle.split(reference)[:2]
    # A path that starts with an empty segment reads back as an authority.
    if "//" in path or (r_scheme is not None and r_authority is None and authority is not None):
        return "it collapses an empty path segment"
    if path == "/":
        return "it drops a path that is only '/'"
    if r_scheme is not None and reference.partition(":")[2][:1] != "/":
        return "it keeps a rootless path rootless after removing dot segments"
    return None


def test_the_rfc3986_package_agrees_apart_from_its_documented_departures() -> None:
    pytest.importorskip("rfc3986")
    assert importlib.metadata.version("rfc3986") == "2.0.0"
    from rfc3986 import uri_reference  # type: ignore[import-untyped]

    rng = random.Random(5)
    segment = ["a", "b", "g", ";", "=", "x:y", "@", "!", "~", "-"]
    agreed = 0
    for _ in range(100_000):
        reference = _reference(rng).replace("%41", "A")
        if reference.count("#") > 1:
            continue
        path = "/".join(
            "".join(rng.choice(segment) for _ in range(rng.randint(1, 3)))
            for _ in range(rng.randint(0, 3))
        )
        authority = rng.choice(["http://a", "https://u@h:8", "s://h.test"])
        base = f"{authority}/{path}{rng.choice(['', '?q', '?', '#f'])}"
        ours = resolve_uri(reference, base)
        theirs = uri_reference(reference).resolve_with(base, strict=True).unsplit()
        if ours == theirs:
            agreed += 1
        else:
            assert _rfc3986_departure(reference, ours), (reference, base, ours, theirs)
    assert agreed > 80_000


@pytest.mark.parametrize(
    ("reference", "resolved"),
    [
        ("!x:y", "http://a/b/c/!x:y"),
        ("a b:c/../d", "http://a/b/c/d"),
        ("1a:b", "http://a/b/c/1a:b"),
        ("_:x?q#f", "http://a/b/c/_:x?q#f"),
        ("a+b.c-d:e", "a+b.c-d:e"),
    ],
)
def test_text_before_a_colon_that_is_not_a_scheme_is_a_relative_path(
    reference: str, resolved: str
) -> None:
    assert resolve_uri(reference, "http://a/b/c/d") == resolved


def test_the_pseudocode_oracle_gives_the_rfc_examples() -> None:
    base = "http://a/b/c/d;p?q"
    assert uri_oracle.resolve("../../../g", base) == "http://a/g"
    assert uri_oracle.resolve("g;x=1/../y", base) == "http://a/b/c/y"
    assert uri_oracle.resolve("http:g", base) == "http:g"
