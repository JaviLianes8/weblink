"""Real servers: follow the pagination Link headers GitHub and GitLab send.

Needs the network, so it runs only with WEBLINKING_LIVE=1.
"""

from __future__ import annotations

import os
import urllib.request

import pytest

from weblinking import find, parse

pytestmark = pytest.mark.skipif(
    os.environ.get("WEBLINKING_LIVE") != "1", reason="set WEBLINKING_LIVE=1 to use the network"
)


def _links(url: str) -> list[str]:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "weblinking"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.headers.get_all("Link") or []


def test_github_pagination_can_be_followed_forward_and_back() -> None:
    first = "https://api.github.com/repos/python/cpython/tags?per_page=5"
    links = parse(_links(first), strict=True)
    following = find(links, "next")
    last = find(links, "last")
    assert following is not None and last is not None
    assert following.uri.endswith("page=2") and find(links, "prev") is None
    back = find(parse(_links(following.uri), strict=True), "prev")
    assert back is not None and back.uri.endswith("page=1")


def test_gitlab_pagination_reads_strictly() -> None:
    links = parse(_links("https://gitlab.com/api/v4/projects?per_page=2"), strict=True)
    following = find(links, "next")
    assert following is not None and "page=2" in following.uri
    assert find(links, "first") is not None
