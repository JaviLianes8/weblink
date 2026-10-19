"""The public API is typed: mypy infers the documented types and rejects wrong ones."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"

SNIPPET = """
from weblinking import Link, build, decode_ext_value, find, find_all, parse, resolve_uri
from weblinking import REGISTERED_RELATIONS, encode_ext_value, is_registered
reveal_type(parse("</a>; rel=next"))
reveal_type(build([Link("/a", {"rel": "next"})]))
reveal_type(find([], "next"))
reveal_type(find_all([], "next"))
reveal_type(Link("/a").pairs)
reveal_type(Link("/a").title)
reveal_type(Link("/a").rels)
reveal_type(decode_ext_value("UTF-8''a"))
reveal_type(resolve_uri("a", "http://b/"))
reveal_type(REGISTERED_RELATIONS)
reveal_type(is_registered("next"))
parse("</a>", True)
parse(b"</a>")
build(["</a>"])
Link("/a", {"rel": 1})
encode_ext_value(b"x")
parse(["</a>; rel=next", "</b>; rel=prev"], strict=True)
Link("/a", [("rel", "next")])
"""


@pytest.fixture(scope="module")
def mypy_output(tmp_path_factory: pytest.TempPathFactory) -> str:
    folder = tmp_path_factory.mktemp("typing")
    target = folder / "snippet.py"
    target.write_text(SNIPPET, encoding="utf-8")
    config = folder / "mypy.ini"
    config.write_text(f"[mypy]\nmypy_path = {SRC.as_posix()}\n", encoding="utf-8")
    cache = str(folder / "cache")
    args = ["--strict", "--config-file", str(config), "--cache-dir", cache, str(target)]
    try:
        from mypy import api
    except ImportError:
        # The interpreter running pytest may lack mypy while the one on PATH has it.
        program = shutil.which("mypy")
        if program is None:
            pytest.skip("mypy is not installed")
        result = subprocess.run([program, *args], capture_output=True, text=True, check=False)
        return result.stdout + result.stderr
    out, err, _ = api.run(args)
    return str(out) + str(err)


def test_functions_return_plain_types(mypy_output: str) -> None:
    revealed = [_revealed(mypy_output, line) for line in range(4, 15)]
    # mypy releases spell a NamedTuple differently; the fallback names the class in all.
    assert revealed[7].endswith("fallback=weblinking._ext.ExtValue]")
    revealed[7] = "ExtValue"
    assert revealed == [
        "list[weblinking._model.Link]",
        "str",
        "weblinking._model.Link | None",
        "list[weblinking._model.Link]",
        "tuple[tuple[str, str], ...]",
        "str | None",
        "tuple[str, ...]",
        "ExtValue",
        "str",
        "frozenset[str]",
        "bool",
    ]


def test_misuse_is_rejected(mypy_output: str) -> None:
    expected = ((15, "call-arg"), (16, "arg-type"), (17, "list-item"), (18, "arg-type"))
    for line, code in (*expected, (19, "arg-type")):
        assert re.search(rf"snippet\.py:{line}: error: .*\[{code}\]", mypy_output), mypy_output


def test_documented_calls_type_check(mypy_output: str) -> None:
    assert "snippet.py:20:" not in mypy_output, mypy_output
    assert "snippet.py:21:" not in mypy_output, mypy_output


def _revealed(output: str, line: int) -> str:
    match = re.search(rf"snippet\.py:{line}: note: Revealed type is \"(.+)\"", output)
    assert match, output
    # Older mypy releases spell builtins with their module prefix.
    return match.group(1).replace("builtins.", "")
