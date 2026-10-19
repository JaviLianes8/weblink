"""The web link value object."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

from ._access import _Access
from ._chars import ascii_lower
from ._errors import need_str
from ._uri import absolute_base, resolve_uri

# Pairs may be tuples, or lists as JSON gives them.
Params = Mapping[str, str] | Iterable[tuple[str, str] | list[str]]


class Link(_Access):
    """A single web link: a target URI reference and its parameters, in order.

    ``params`` may be a mapping or an iterable of ``(name, value)`` pairs (tuples, or
    lists as JSON gives them); pairs keep parameters that repeat, such as ``hreflang``.
    The ASCII letters of names are lower-cased, since RFC 8288 parameter names are
    case-insensitive (other characters never fold); values are kept as given.
    Links are immutable, hashable, picklable, and equal when their target and parameter
    pairs are equal. ``TypeError`` is raised for anything but ``str`` names and values.

    >>> link = Link("/fr", [("Rel", "alternate"), ("hreflang", "fr"), ("hreflang", "fr-CA")])
    >>> link
    Link('/fr', [('rel', 'alternate'), ('hreflang', 'fr'), ('hreflang', 'fr-CA')])
    >>> link.rel, link.hreflang, link.hreflangs
    ('alternate', 'fr', ('fr', 'fr-CA'))
    """

    __slots__ = ("_pairs", "_uri")
    _uri: str
    _pairs: tuple[tuple[str, str], ...]

    def __init__(self, uri: str, params: Params = ()) -> None:
        uri = need_str(uri, "uri")
        if isinstance(params, (str, bytes, bytearray)):
            raise TypeError("params must be a mapping or an iterable of (name, value) pairs")
        items = params.items() if isinstance(params, Mapping) else params
        pairs = []
        for item in items:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise TypeError("each parameter must be a (name, value) pair")
            name = need_str(item[0], "a parameter name")
            pairs.append((ascii_lower(name), need_str(item[1], "a parameter value")))
        object.__setattr__(self, "_uri", uri)
        object.__setattr__(self, "_pairs", tuple(pairs))

    if not TYPE_CHECKING:  # hidden from type checkers so they flag assignments themselves

        def __setattr__(self, name: str, value: object) -> None:
            raise AttributeError("Link is immutable")

        def __delattr__(self, name: str) -> None:
            raise AttributeError("Link is immutable")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Link):
            return NotImplemented
        return self._uri == other._uri and self._pairs == other._pairs

    def __hash__(self) -> int:
        return hash((self._uri, self._pairs))

    def __repr__(self) -> str:
        names = [name for name, _ in self._pairs]
        shown: object = dict(self._pairs) if len(set(names)) == len(names) else list(self._pairs)
        return f"Link({self._uri!r}, {shown!r})"

    def __reduce__(self) -> tuple[type[Link], tuple[str, tuple[tuple[str, str], ...]]]:
        return (Link, (self._uri, self._pairs))

    @property
    def uri(self) -> str:
        """The target URI reference as written, relative or absolute.

        >>> Link("../b", {"rel": "up"}).uri
        '../b'
        """
        return self._uri

    def resolve(self, base: str) -> Link:
        """A copy whose target and every ``anchor`` are resolved against ``base`` (RFC 3986).

        >>> Link("../b", {"rel": "up", "anchor": "#x"}).resolve("http://a.test/c/d")
        Link('http://a.test/b', {'rel': 'up', 'anchor': 'http://a.test/c/d#x'})
        """
        pairs = [
            (name, resolve_uri(value, base) if name == "anchor" else value)
            for name, value in self._pairs
        ]
        return Link(resolve_uri(self._uri, base), pairs)

    def context(self, base: str) -> str:
        """The link context: the first ``anchor`` resolved against ``base``, or ``base``.

        Raises :class:`LinkError` when ``base`` is not an absolute URI, as
        :func:`resolve_uri` does.

        >>> Link("/b", {"rel": "up"}).context("http://a.test/c")
        'http://a.test/c'
        """
        anchor = self.anchor
        return absolute_base(base) if anchor is None else resolve_uri(anchor, base)
