"""Huge hostile input costs linear time and fails with short messages.

Each shape is timed at n and 4n characters (best of three); quadratic work would take
about 16 times longer, linear work about 4 times.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import pytest

from weblinking import Link, LinkError, build, decode_ext_value, parse, resolve_uri
from weblinking._cli import field_values

N = 50_000
SHAPES: dict[str, Callable[[int], str]] = {
    "open brackets": lambda n: "<" * n,
    "many links": lambda n: "<a>;rel=x," * (n // 10),
    "semicolons": lambda n: "<a>" + ";" * n,
    "parameters": lambda n: "<a>" + ";a=b" * (n // 4),
    "escapes": lambda n: '<a>;t="' + "\\a" * (n // 2),
    "open quotes": lambda n: '<a>;t="' * (n // 7),
    "junk": lambda n: "x" * n,
    "junk and commas": lambda n: "x," * (n // 2),
    "whitespace": lambda n: " \t" * (n // 2),
    "equals signs": lambda n: "<a>;a" + "=" * n,
    "relation types": lambda n: '<a>;rel="' + "next " * (n // 5) + '"',
    "starred value": lambda n: "<a>;rel=x;title*=UTF-8''" + "%41" * (n // 3),
    "escaped target": lambda n: "<" + "%41" * (n // 3) + ">;rel=x",
    "slashes": lambda n: "<" + "/" * n + ">;rel=x",
    "response head": lambda n: "HTTP/1.1 200\r\n" + "Link: <a>; rel=x\r\n" * (n // 18),
    "folded head": lambda n: "HTTP/1.1 200\r\nLink: <a>\r\n" + " ;rel=x\r\n" * (n // 9),
}


def _best(work: Callable[[], object]) -> float:
    times = []
    for _ in range(3):
        start = time.perf_counter()
        work()
        times.append(time.perf_counter() - start)
    return min(times)


def _read(text: str) -> None:
    parse(text)
    try:
        parse(text, strict=True)
    except LinkError as error:
        assert len(str(error)) < 300
    field_values(text)


def _linear(work: Callable[[int], object]) -> None:
    small, large = _best(lambda: work(N)), _best(lambda: work(4 * N))
    assert large < max(10 * small, 0.05), (small, large)


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_parsing_takes_linear_time(shape: str) -> None:
    _linear(lambda n: _read(SHAPES[shape](n)))


def test_resolution_takes_linear_time() -> None:
    _linear(lambda n: resolve_uri("a/" * (n // 2) + "../" * (n // 6), "http://a/b/c"))
    _linear(lambda n: resolve_uri("/.." * (n // 3), "http://a/b/c"))


def test_ext_values_take_linear_time() -> None:
    _linear(lambda n: decode_ext_value("UTF-8''" + "%C3%A4" * (n // 6)))


def test_links_with_many_parameters_take_linear_time() -> None:
    def work(n: int) -> None:
        link = Link("/a", [("rel", "x"), *[("hreflang", "en")] * n])
        assert link.has_rel("X") and link.get("title") is None and len(link.hreflangs) == n
        build([link])

    _linear(work)


def test_a_megabyte_in_every_error_path_gives_a_short_message() -> None:
    huge = "\x01" * 1_000_000
    calls: list[Callable[[], object]] = [
        lambda: parse("<" + huge + ">; rel=x", strict=True),
        lambda: parse("<a>; rel=x; t=" + huge, strict=True),
        lambda: parse('<a>; rel=x; t="' + huge + '"', strict=True),
        lambda: parse("<a>; rel=x; t*=" + huge, strict=True),
        lambda: build([Link("/a", {"rel": "x", "t": huge})]),
        lambda: build([Link("/a", {"rel": "x", "t*": huge})]),
        lambda: decode_ext_value(huge),
        lambda: resolve_uri("a", huge),
    ]
    for call in calls:
        with pytest.raises(LinkError) as caught:
            call()
        assert len(str(caught.value)) < 300
