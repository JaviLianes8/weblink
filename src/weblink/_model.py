"""The web link value object."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

from ._errors import LinkError
from ._ext import decode_ext_value
from ._registry import normalise_rel
from ._uri import resolve_uri

Params = Mapping[str, str] | Iterable[tuple[str, str]]


class Link:
    """A single web link: a target URI reference and its parameters, in order.

    ``params`` may be a mapping or a sequence of ``(name, value)`` pairs; the pair form
    keeps parameters that repeat, such as several ``hreflang``. Names are lower-cased,
    since RFC 8288 parameter names are case-insensitive. Links are immutable, hashable,
    and equal when their target and parameter pairs are equal.
    """

    __slots__ = ("_pairs", "_uri")
    _uri: str
    _pairs: tuple[tuple[str, str], ...]

    def __init__(self, uri: str, params: Params = ()) -> None:
        if not isinstance(uri, str):
            raise TypeError(f"uri must be str, not {type(uri).__name__}")
        items = params.items() if isinstance(params, Mapping) else params
        pairs = []
        for name, value in items:
            if not isinstance(name, str) or not isinstance(value, str):
                raise TypeError("parameter names and values must be str")
            pairs.append((name.lower(), value))
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
        """Every raw value of parameter ``name``, in order."""
        key = name.lower()
        return [value for pname, value in self._pairs if pname == key]

    def get(self, name: str) -> str | None:
        """The first value of ``name``, preferring a decodable RFC 8187 ``name*`` form.

        RFC 8288 section 3.4 says to use the starred value when both are present and
        allows falling back to the plain one when the starred value cannot be decoded.
        """
        key = name.lower()
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
        """The raw ``rel`` value, which may hold several space separated types."""
        return self.params.get("rel")

    @property
    def rels(self) -> tuple[str, ...]:
        """The relation types of ``rel``: registered names lower-cased, URIs as written."""
        return tuple(normalise_rel(rel) for rel in (self.rel or "").split())

    def has_rel(self, relation_type: str) -> bool:
        """True when this link carries ``relation_type``, compared as RFC 8288 says."""
        return normalise_rel(relation_type) in self.rels

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
        """A copy whose target and ``anchor`` are resolved against ``base`` (RFC 3986)."""
        pairs = [
            (name, resolve_uri(value, base) if name == "anchor" else value)
            for name, value in self._pairs
        ]
        return Link(resolve_uri(self._uri, base), pairs)

    def context(self, base: str) -> str:
        """The link context: ``anchor`` resolved against ``base``, or ``base`` itself."""
        anchor = self.anchor
        return base if anchor is None else resolve_uri(anchor, base)
