"""The web link value object."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

from ._errors import LinkError, need_str
from ._ext import decode_ext_value
from ._registry import normalise_rel
from ._uri import absolute_base, resolve_uri

Params = Mapping[str, str] | Iterable[tuple[str, str]]


class Link:
    """A single web link: a target URI reference and its parameters, in order.

    ``params`` may be a mapping or an iterable of ``(name, value)`` pairs (tuples, or
    lists as JSON gives them); pairs keep parameters that repeat, such as ``hreflang``.
    Names are lower-cased, since RFC 8288 parameter names are case-insensitive; values
    are kept as given.
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
            pairs.append((name.lower(), need_str(item[1], "a parameter value")))
        object.__setattr__(self, "_uri", uri)
        object.__setattr__(self, "_pairs", tuple(pairs))

    if not TYPE_CHECKING:  # hidden from type checkers so they flag assignments themselves

        def __setattr__(self, name: str, value: object) -> None:
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
        """The target URI reference as written, relative or absolute."""
        return self._uri

    @property
    def pairs(self) -> tuple[tuple[str, str], ...]:
        """Every parameter in order, repeated names included, values as written."""
        return self._pairs

    @property
    def params(self) -> dict[str, str]:
        """A new dict of parameters; when a name repeats, its first value wins."""
        out: dict[str, str] = {}
        for name, value in self._pairs:
            out.setdefault(name, value)
        return out

    def get_all(self, name: str) -> list[str]:
        """Every raw value of parameter ``name`` (any case), in order.

        >>> Link("/a", [("rel", "x"), ("hreflang", "en"), ("HrefLang", "fr")]).get_all("HREFLANG")
        ['en', 'fr']
        """
        key = need_str(name, "name").lower()
        return [value for pname, value in self._pairs if pname == key]

    def get(self, name: str) -> str | None:
        """The first value of ``name``, preferring a decodable RFC 8187 ``name*`` form.

        RFC 8288 section 3.4 says to use the starred value when both are present and
        allows falling back to the plain one when the starred value cannot be decoded.
        Only the first starred value is tried. ``None`` when neither form is present.

        >>> link = Link("/a", {"title": "Next", "title*": "UTF-8'de'n%C3%A4chstes"})
        >>> link.get("title"), link.get("title*"), link.get("type")
        ('nächstes', "UTF-8'de'n%C3%A4chstes", None)
        """
        key = need_str(name, "name").lower()
        if not key.endswith("*"):
            for value in self.get_all(key + "*"):
                try:
                    return decode_ext_value(value).value
                except LinkError:
                    break
        values = self.get_all(key)
        return values[0] if values else None

    @property
    def rel(self) -> str | None:
        """The raw first ``rel`` value, which may hold several space separated types."""
        return self.params.get("rel")

    @property
    def rels(self) -> tuple[str, ...]:
        """The relation types of ``rel``, ASCII lower-cased as RFC 8288 compares them.

        >>> Link("/a", {"rel": "Next  last"}).rels
        ('next', 'last')
        """
        return tuple(normalise_rel(rel) for rel in (self.rel or "").split())

    def has_rel(self, relation_type: str) -> bool:
        """True when ``rels`` holds ``relation_type``, compared without ASCII case.

        >>> Link("/a", {"rel": "next last"}).has_rel("NEXT")
        True
        """
        return normalise_rel(need_str(relation_type, "relation_type")) in self.rels

    @property
    def rev(self) -> str | None:
        """The deprecated ``rev`` value, raw."""
        return self.params.get("rev")

    @property
    def anchor(self) -> str | None:
        """The ``anchor`` parameter: the link context when it is not the resource itself."""
        return self.params.get("anchor")

    @property
    def title(self) -> str | None:
        """The title, decoded from ``title*`` when present and valid, else ``title``."""
        return self.get("title")

    @property
    def type(self) -> str | None:
        """The ``type`` hint: the media type expected at the target."""
        return self.params.get("type")

    @property
    def media(self) -> str | None:
        """The ``media`` attribute: the media query the target is intended for."""
        return self.params.get("media")

    @property
    def hreflang(self) -> str | None:
        """The first ``hreflang`` value."""
        return self.params.get("hreflang")

    @property
    def hreflangs(self) -> tuple[str, ...]:
        """Every ``hreflang`` value: one link may name several languages."""
        return tuple(self.get_all("hreflang"))

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
