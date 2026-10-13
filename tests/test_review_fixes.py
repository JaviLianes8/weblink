"""Regression tests for the findings of the independent review of the 0.2.0 round."""

from __future__ import annotations

import io
import json
import sys

import pytest

from weblink import LinkError, parse, resolve_uri
from weblink._cli import field_values, main


@pytest.mark.parametrize("rel", ["X-Custom", "nExt-thing", "Ab"])
def test_strict_rejects_unregistered_names_outside_loalpha(rel: str) -> None:
    with pytest.raises(LinkError, match="relation type"):
        parse(f"</a>; rel={rel}", strict=True)


def test_strict_accepts_registered_names_in_any_case() -> None:
    assert parse("</a>; rel=Next", strict=True)[0].rels == ("next",)


@pytest.mark.parametrize(
    "uri",
    ["#a#b", "http://[x", "http://[]/", "1a:b", "a/b[c]", "?q]", "http://h:8x/", "//u@v@h/"],
)
def test_strict_rejects_targets_with_a_broken_structure(uri: str) -> None:
    with pytest.raises(LinkError, match="URI reference"):
        parse(f"<{uri}>; rel=next", strict=True)


@pytest.mark.parametrize(
    "uri", ["http://[2001:db8::1]:80/a", "//u:p@h:/", "urn:a:b", "a/b:c", "#f/?", "?a=:@/"]
)
def test_strict_accepts_valid_structures(uri: str) -> None:
    assert parse(f"<{uri}>; rel=next", strict=True)[0].uri == uri


def test_dot_segment_removal_takes_linear_time() -> None:
    # Two megabytes of "../": quadratic slicing would run for many minutes here.
    assert resolve_uri("../" * 700_000 + "g", "http://x/a/b") == "http://x/g"


def _cli(*argv: str, stdin: str = "") -> tuple[int, str]:
    out = io.StringIO()
    status = main(list(argv), stdin=io.StringIO(stdin), stdout=out)
    return status, out.getvalue()


def test_cli_output_is_ascii_json() -> None:
    status, out = _cli("</a>; rel=next; title=\"x\"; title*=UTF-8''%E6%BC%A2")
    assert status == 0 and out.isascii()
    assert json.loads(out)[0]["params"][2] == ["title*", "UTF-8''%E6%BC%A2"]
    status, out = _cli("</caf\u00e9>; rel=next")
    assert status == 0 and out.isascii() and json.loads(out)[0]["uri"] == "/caf\u00e9"


def test_cli_reads_obs_text_bytes_from_standard_input(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = io.TextIOWrapper(io.BytesIO(b'Link: <a>; rel=next; title="caf\xe9"\r\n'), "utf-8")
    monkeypatch.setattr(sys, "stdin", raw)
    out = io.StringIO()
    assert main([], stdout=out) == 0
    assert json.loads(out.getvalue())[0]["params"][1] == ["title", "caf\u00e9"]


def test_a_head_without_a_link_field_has_no_links() -> None:
    head = "HTTP/1.1 200 OK\r\nX-Foo: a, <https://evil/>; rel=next\r\n\r\n"
    assert field_values(head) == []
    assert _cli("--strict", stdin="HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n") == (
        0,
        "[]\n",
    )


def test_the_body_after_a_head_is_ignored() -> None:
    head = "HTTP/1.1 200 OK\nLink: </1>; rel=next\n\nlink: </evil>; rel=next\n"
    assert field_values(head) == ["</1>; rel=next"]


def test_only_the_final_response_of_a_redirect_chain_counts() -> None:
    chain = (
        "HTTP/1.1 301 Moved\r\nLink: </old>; rel=prev\r\nLocation: /n\r\n\r\n"
        "HTTP/1.1 200 OK\r\nLink: </new>; rel=next\r\n\r\n"
    )
    assert field_values(chain) == ["</new>; rel=next"]


def test_unicode_line_separators_do_not_split_a_value() -> None:
    text = 'Link: </a>; rel=next; title="x\u2028y", </b>; rel=prev'
    assert field_values(text) == ['</a>; rel=next; title="x\u2028y", </b>; rel=prev']
    assert len(parse(field_values(text))) == 2


@pytest.mark.parametrize("uri", ["a%", "a%4", "%"])
def test_a_truncated_percent_escape_is_not_a_uri_reference(uri: str) -> None:
    with pytest.raises(LinkError, match="URI reference"):
        parse(f"<{uri}>; rel=next", strict=True)
