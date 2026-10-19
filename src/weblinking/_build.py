"""Build a Link header value from links, refusing what the header cannot carry."""

from __future__ import annotations

from collections.abc import Iterable

from ._check import check_link
from ._errors import LinkError, quote
from ._model import Link


def build(links: Iterable[Link]) -> str:
    """Serialise links into an RFC 8288 ``Link`` header value.

    Each link becomes ``<uri>; name="value"`` and the links are joined with ``", "``.
    Values are quoted and escaped; RFC 8187 starred values (``title*``) are written bare,
    as RFC 8187 requires. Raises :class:`LinkError` for a link :func:`parse` would reject
    in strict mode (no ``rel``, a target that is not a URI reference, a name that is not
    a token, a starred value that is not an ext-value) and for values holding control
    characters or non-ASCII text, which would break or inject header lines: encode such
    text with :func:`encode_ext_value` and send it as ``title*``. ``TypeError`` is raised
    for anything but an iterable of :class:`Link`. No links give the empty string.

    >>> build([Link("/page/2", {"rel": "next"}), Link("/page/9", {"rel": "last"})])
    '</page/2>; rel="next", </page/9>; rel="last"'
    >>> print(build([Link("/a", {"rel": "next", "title": 'say "hi"'})]))
    </a>; rel="next"; title="say \\"hi\\""
    """
    if isinstance(links, (Link, str, bytes, bytearray)):
        raise TypeError(f"build takes an iterable of Link objects, not {type(links).__name__}")
    return ", ".join(_build_one(link) for link in links)


def _build_one(link: Link) -> str:
    if not isinstance(link, Link):
        raise TypeError(f"build takes Link objects, not {type(link).__name__}")
    check_link(link)
    parts = [f"<{link.uri}>"]
    for name, value in link.pairs:
        if name.endswith("*"):
            parts.append(f"{name}={value}")
            continue
        for c in value:
            if not (c == "\t" or " " <= c <= "~"):
                raise LinkError(
                    f"{quote(name)} value has {c!r}; send non-ASCII text as "
                    f"{quote(name + '*')} with encode_ext_value"
                )
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'{name}="{escaped}"')
    return "; ".join(parts)
