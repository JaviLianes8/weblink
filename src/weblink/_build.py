"""Build a Link header value from a list of links."""

from __future__ import annotations

from collections.abc import Iterable

from ._errors import LinkError
from ._model import Link


def build(links: Iterable[Link]) -> str:
    """Serialise links into an RFC 8288 ``Link`` header value.

    Each link becomes ``<uri>; name="value"`` and the parts are joined with a
    comma. Parameter values are always quoted and their quotes escaped, so the
    result parses back to the same links.
    """
    return ", ".join(_build_one(link) for link in links)


def _build_one(link: Link) -> str:
    if not link.uri:
        raise LinkError("a link needs a non-empty uri")
    parts = [f"<{link.uri}>"]
    parts.extend(_build_param(name, value) for name, value in link.params.items())
    return "; ".join(parts)


def _build_param(name: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'{name}="{escaped}"'
