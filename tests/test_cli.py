"""The weblinking command, driven in process with injected streams."""

from __future__ import annotations

import io
import json

import pytest

from weblinking._cli import field_values, main

# A response head shaped like `curl -sI` output; the Link value is the live header
# https://api.github.com/repos/JaviLianes8/weblink/commits?per_page=1&page=1 returned on
# 2026-10-13.
HEAD = (
    "HTTP/2 200\r\n"
    "content-type: application/json; charset=utf-8\r\n"
    "Link: <https://api.github.com/repositories/1414908074/commits?per_page=1&page=2>; "
    'rel="next", <https://api.github.com/repositories/1414908074/commits?per_page=1&page=2>; '
    'rel="last"\r\n'
    "x-ratelimit-remaining: 59\r\n"
)


def _run(*argv: str, stdin: str = "") -> tuple[int, object]:
    out = io.StringIO()
    status = main(list(argv), stdin=io.StringIO(stdin), stdout=out)
    return status, json.loads(out.getvalue()) if status == 0 else None


def test_a_response_head_on_stdin() -> None:
    status, rows = _run(stdin=HEAD)
    assert status == 0
    assert isinstance(rows, list)
    assert [row["rels"] for row in rows] == [["next"], ["last"]]
    assert rows[0]["params"] == [["rel", "next"]]


def test_a_header_value_as_an_argument() -> None:
    status, rows = _run("</b>; rel=\"Next\"; title*=UTF-8''caf%C3%A9")
    assert status == 0
    assert rows == [
        {"uri": "/b", "rels": ["next"], "params": [["rel", "Next"], ["title*", "UTF-8''caf%C3%A9"]]}
    ]


def test_base_resolves_targets() -> None:
    status, rows = _run("--base", "https://a.test/x/y", '<../z>; rel="up"')
    assert status == 0
    assert rows == [{"uri": "https://a.test/z", "rels": ["up"], "params": [["rel", "up"]]}]


def test_errors_exit_with_status_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert _run("--strict", "<a>; title=x")[0] == 2
    assert "rel" in capsys.readouterr().err
    assert _run("--base", "relative", "<a>; rel=x")[0] == 2
    assert "absolute" in capsys.readouterr().err


def test_no_links_prints_an_empty_list() -> None:
    assert _run(stdin="HTTP/1.1 204 No Content\n\n") == (0, [])


def test_field_values_reads_every_link_line_and_folding() -> None:
    head = "LINK: </1>; rel=next\nOther: x\nlink:</2>;\n\trel=last\n continued=1\nlinkx: </3>"
    assert field_values(head) == ["</1>; rel=next", "</2>; rel=last continued=1"]


def test_field_values_takes_bare_text_as_one_value() -> None:
    assert field_values("</1>; rel=next,\n </2>; rel=last\n") == ["</1>; rel=next, </2>; rel=last"]


def test_python_dash_m_runs_the_command() -> None:
    import runpy
    import sys

    argv, stdout = sys.argv, sys.stdout
    sys.argv, sys.stdout = ["weblinking", "</a>; rel=next"], io.StringIO()
    try:
        with pytest.raises(SystemExit) as stopped:
            runpy.run_module("weblinking", run_name="__main__")
        printed = sys.stdout.getvalue()
    finally:
        sys.argv, sys.stdout = argv, stdout
    assert stopped.value.code == 0
    assert json.loads(printed)[0]["uri"] == "/a"
