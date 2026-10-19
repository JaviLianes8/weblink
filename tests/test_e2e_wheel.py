"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with WEBLINKING_E2E=1.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("WEBLINKING_E2E") != "1", reason="set WEBLINKING_E2E=1 to build and install"
)

PROGRAM = r"""
import importlib.metadata, importlib.resources, pickle
import weblinking
from weblinking import (
    ExtValue, Link, LinkError, REGISTERED_RELATIONS, build, decode_ext_value,
    encode_ext_value, find, find_all, is_registered, parse, resolve_uri,
)

assert "site-packages" in weblinking.__file__, weblinking.__file__
assert importlib.metadata.version("weblinking") == weblinking.__version__
assert importlib.resources.files("weblinking").joinpath("py.typed").is_file()

header = (
    "</TheBook/chapter2>; rel=\"previous\"; title*=UTF-8'de'letztes%20Kapitel, "
    "</TheBook/chapter4>; rel=\"next\"; title*=UTF-8'de'n%c3%a4chstes%20Kapitel"
)
links = parse(header, strict=True)
assert [link.title for link in links] == ["letztes Kapitel", "nächstes Kapitel"]
nxt = find(links, "NEXT")
assert nxt is not None and nxt.resolve("http://a/b/c").uri == "http://a/TheBook/chapter4"
assert find_all(links, "previous") == links[:1]
assert parse(build(links), strict=True) == links
assert resolve_uri("http:g", "http://a/b/c/d;p?q") == "http:g"
assert decode_ext_value(encode_ext_value("€", "en")) == ExtValue("€", "en", "UTF-8")
assert is_registered("openid2.local_id") and "next" in REGISTERED_RELATIONS
multi = parse(["</a>; rel=alternate; hreflang=en; hreflang=fr"])[0]
assert multi.hreflangs == ("en", "fr") and pickle.loads(pickle.dumps(multi)) == multi
for call in (
    lambda: parse("</a>; rel=next; rel=prev", strict=True),
    lambda: build([Link("/a", {"rel": "next", "title": "x\r\nSet-Cookie: a=b"})]),
    lambda: build([Link("/a", {"title": "no rel"})]),
    lambda: decode_ext_value("UTF-8''%FF"),
):
    try:
        call()
    except LinkError as error:
        assert isinstance(error, ValueError)
    else:
        raise AssertionError("expected LinkError")
for wrong in (lambda: find(links, None), lambda: Link("/a", "rel"), lambda: build(links[0])):
    try:
        wrong()
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError")
try:
    resolve_uri("a", "x" * 10_000)
except LinkError as error:
    assert len(str(error)) < 300 and error.position is None
assert resolve_uri("a b:c", "http://h/x/y") == "http://h/x/a b:c"
assert Link.__module__ == LinkError.__module__ == "weblinking"
requires = importlib.metadata.requires("weblinking") or []
assert requires and all("extra ==" in item for item in requires), requires
print("e2e ok")
"""


def _run(
    *cmd: str | Path, cwd: Path | None = None, stdin: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, input=stdin, capture_output=True, check=False
    )


def test_installed_wheel_end_to_end(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    built = _run(sys.executable, "-m", "build", "--outdir", dist, ROOT)
    assert built.returncode == 0, built.stderr
    (wheel,) = dist.glob("weblinking-*.whl")
    (sdist,) = dist.glob("weblinking-*.tar.gz")
    names = zipfile.ZipFile(wheel).namelist()
    assert "weblinking/py.typed" in names
    assert not any(name.startswith(("tests/", "scripts/")) for name in names)
    entry_points = next(name for name in names if name.endswith("entry_points.txt"))
    assert "weblinking = weblinking._cli:main" in zipfile.ZipFile(wheel).read(entry_points).decode()
    listing = _run(sys.executable, "-m", "tarfile", "-l", sdist).stdout.decode()
    assert "IMPROVEMENTS-round" not in listing and "CERT-1.0" not in listing
    assert "GUIDE.md" in listing and "LICENSE" in listing and "node_modules" not in listing
    assert any(name.endswith("licenses/LICENSE") for name in names)
    metadata = next(name for name in names if name.endswith("METADATA"))
    text = zipfile.ZipFile(wheel).read(metadata).decode()
    assert "Version: 1.0.0" in text and "Development Status :: 5 - Production/Stable" in text
    assert "tests/upstream/MANIFEST.json" in listing
    for fetched in ("rfc8288.txt", "rfc8187.txt", "rfc3986.txt", "rfc9110.txt"):
        assert fetched not in listing, fetched
    assert "link-relations-1.csv" not in listing and "github-pagination.md" not in listing
    assert "tests/test_sources.py" in listing and "scripts/fetch_upstream.py" in listing

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / "python"
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr

    # Run from an empty folder so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.decode().strip() == "e2e ok"

    head = b'HTTP/1.1 200 OK\r\nLink: <../b>; rel="Next"\r\n\r\n'
    script = bindir / ("weblinking.exe" if sys.platform == "win32" else "weblinking")
    for command in ([script], [python, "-m", "weblinking"]):
        shown = _run(*command, "--base", "https://a.test/x/y", cwd=work, stdin=head)
        assert shown.returncode == 0, shown.stderr
        rows = json.loads(shown.stdout)
        assert rows == [{"uri": "https://a.test/b", "rels": ["next"], "params": [["rel", "Next"]]}]
    failed = _run(script, "--strict", "junk", cwd=work)
    assert failed.returncode == 2 and b"expected '<'" in failed.stderr
