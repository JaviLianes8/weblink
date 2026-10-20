"""Independent Link header parsers as oracles: httplink, ietfparse, requests and the
http-link-header package for Node.js.

None is a runtime dependency. Each test skips when its oracle is missing: the `dev` extra
installs httplink 0.2.0, ietfparse 1.9.0 and requests 2.34.2, and `npm install --prefix
tests/upstream http-link-header@1.1.4` the Node.js one (the folder is ignored by git).
The headers come from the grammar generator in `header_gen.py`; where an oracle departs
from RFC 8288 the inputs it cannot read are left out by a stated rule, and that rule is
asserted too.
"""

from __future__ import annotations

import importlib.metadata
import json
import random
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conftest import UPSTREAM
from header_gen import SINGLE, Header, header

from weblinking import Link, decode_ext_value, parse

ROOT = Path(__file__).resolve().parents[1]
SEEDS = [8288, 9110, 8187]


def _pinned(module: str, distribution: str, version: str) -> Any:
    found = pytest.importorskip(module)
    assert importlib.metadata.version(distribution) == version
    return found


def _headers(seed: int, *, tight: bool = False, plain: bool = False) -> list[Header]:
    rng = random.Random(seed)
    return [header(rng, tight=tight, plain=plain) for _ in range(4000)]


def _ours(item: Header) -> list[tuple[str, list[tuple[str, str]]]]:
    return [(link.uri, list(link.pairs)) for link in parse(item.text, strict=True)]


def _plain(item: Header) -> bool:
    """No value holds whitespace, a delimiter or a quote, nothing is escaped, no tabs."""
    values = [value for _, pairs in item.links for _, value in pairs]
    awkward = any(c in value for value in values for c in ' 	,;="')
    uris = "".join(uri for uri, _ in item.links)
    once = all(len({n for n, _ in pairs}) == len(pairs) for _, pairs in item.links)
    return all(values) and not awkward and not any(c in uris for c in "'(),;=") and once


@pytest.mark.parametrize("seed", SEEDS)
def test_the_generated_pairs_are_what_strict_parsing_reads(seed: int) -> None:
    for item in _headers(seed):
        assert _ours(item) == item.links, item.text


@pytest.mark.parametrize("seed", SEEDS)
def test_httplink_reads_the_same_links(seed: int) -> None:
    httplink = _pinned("httplink", "httplink", "0.2.0")
    skipped = 0
    for item in _headers(seed):
        try:
            found = httplink.parse_link_header(item.text).links
        except ValueError as error:
            # httplink requires a language in every ext-value; RFC 8187 makes it optional.
            assert "Bad extended value" in str(error) and "''" in item.text, item.text
            skipped += 1
            continue
        theirs = [(link.target, [(n.lower(), v) for n, v in link.attributes]) for link in found]
        assert theirs == _ours(item), item.text
    assert skipped < 1000


@pytest.mark.parametrize("seed", SEEDS)
def test_ietfparse_reads_the_same_links(seed: int) -> None:
    headers = _pinned("ietfparse.headers", "ietfparse", "1.9.0")
    for item in _headers(seed, plain=True):
        assert _plain(item) and "\\" not in item.text and "	" not in item.text, item.text
        # ietfparse lower-cases several values and does not take leading whitespace.
        found = headers.parse_link(item.text.strip(), strict=False)
        theirs = [(x.target, [(n.lower(), v.lower()) for n, v in x.parameters]) for x in found]
        ours = [(uri, [(n, v.lower()) for n, v in pairs]) for uri, pairs in _ours(item)]
        assert theirs == ours, item.text


@pytest.mark.parametrize("seed", SEEDS)
def test_requests_reads_the_same_links(seed: int) -> None:
    utils = _pinned("requests.utils", "requests", "2.34.2")
    for item in _headers(seed, plain=True):
        # requests splits on every ";" and keeps one value per name: plain headers only.
        theirs = [{k.lower(): v for k, v in d.items()} for d in utils.parse_header_links(item.text)]
        assert theirs == [{"url": uri, **dict(pairs)} for uri, pairs in _ours(item)], item.text


def _node(texts: list[str]) -> list[Any]:
    node = shutil.which("node")
    package = UPSTREAM / "node_modules" / "http-link-header" / "package.json"
    if node is None or not package.is_file():
        pytest.skip("node or http-link-header is missing")
    assert json.loads(package.read_text(encoding="utf-8"))["version"] == "1.1.4"
    script = str(ROOT / "scripts" / "link_oracle.js")
    data = json.dumps(texts).encode("utf-8")
    done = subprocess.run([node, script, str(UPSTREAM)], input=data, capture_output=True)
    assert done.returncode == 0, done.stderr
    result: list[Any] = json.loads(done.stdout.decode("utf-8"))
    return result


def _as_node_refs(link: Link) -> list[dict[str, Any]]:
    """The refs http-link-header documents: one per relation type, first value of the
    single parameters, repeats as lists, type lower-cased, starred values decoded."""
    ref: dict[str, Any] = {"uri": link.uri}
    for name, value in link.pairs:
        if name in ref and name in SINGLE:
            continue
        if name.endswith("*"):
            decoded = decode_ext_value(value)
            ref[name] = {"language": decoded.language.lower(), "encoding": None}
            ref[name]["value"] = decoded.value
        elif name in ref:
            ref[name] = [*ref[name], value] if isinstance(ref[name], list) else [ref[name], value]
        else:
            ref[name] = value.lower() if name == "type" else value
    return [{**ref, "rel": rel} for rel in (link.rel or "").split(" ")]


def _trimmed(value: Any) -> Any:
    # http-link-header keeps the whitespace after an unquoted value.
    if isinstance(value, str):
        return value.rstrip(" \t")
    if isinstance(value, list):
        return [_trimmed(item) for item in value]
    if isinstance(value, dict):
        return {key: _trimmed(item) for key, item in value.items()}
    return value


@pytest.mark.parametrize("seed", SEEDS)
def test_the_node_reference_reads_the_same_links(seed: int) -> None:
    # It mistakes whitespace between a value and the next "," or ";" for part of the
    # value or the start of a name, so these headers have none there.
    items = _headers(seed, tight=True)
    for item, refs in zip(items, _node([item.text for item in items]), strict=True):
        ours = [ref for link in parse(item.text, strict=True) for ref in _as_node_refs(link)]
        assert _trimmed(refs) == _trimmed(ours), item.text
