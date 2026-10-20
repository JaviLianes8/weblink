"""The parameter accessors of a link, kept apart from how a link is built and compared."""

from __future__ import annotations

from ._chars import SPACES, ascii_lower
from ._errors import LinkError, need_str
from ._ext import decode_ext_value
from ._registry import normalise_rel


class _Access:
    __slots__ = ()
    _pairs: tuple[tuple[str, str], ...]

    @property
    def pairs(self) -> tuple[tuple[str, str], ...]:
        """Every parameter in order, repeated names included, values as written.

        >>> from weblinking import Link
        >>> Link("/a", [("Rel", "next"), ("x", "1"), ("x", "2")]).pairs
        (('rel', 'next'), ('x', '1'), ('x', '2'))
        """
        return self._pairs

    @property
    def params(self) -> dict[str, str]:
        """A new dict of parameters; when a name repeats, its first value wins.

        >>> from weblinking import Link
        >>> Link("/a", [("rel", "next"), ("x", "1"), ("x", "2")]).params
        {'rel': 'next', 'x': '1'}
        """
        out: dict[str, str] = {}
        for name, value in self._pairs:
            out.setdefault(name, value)
        return out

    def get_all(self, name: str) -> list[str]:
        """Every raw value of parameter ``name`` (ASCII letters in any case), in order.

        >>> from weblinking import Link
        >>> Link("/a", [("rel", "x"), ("hreflang", "en"), ("HrefLang", "fr")]).get_all("HREFLANG")
        ['en', 'fr']
        """
        key = ascii_lower(need_str(name, "name"))
        return [value for pname, value in self._pairs if pname == key]

    def get(self, name: str) -> str | None:
        """The first value of ``name``, preferring a decodable RFC 8187 ``name*`` form.

        RFC 8288 section 3.4 says to use the starred value when both are present and
        allows falling back to the plain one when the starred value cannot be decoded.
        Only the first starred value is tried. ``None`` when neither form is present.

        >>> from weblinking import Link
        >>> link = Link("/a", {"title": "Next", "title*": "UTF-8'de'n%C3%A4chstes"})
        >>> link.get("title"), link.get("title*"), link.get("type")
        ('nächstes', "UTF-8'de'n%C3%A4chstes", None)
        """
        key = ascii_lower(need_str(name, "name"))
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
        """The raw first ``rel`` value, which may hold several types; ``rel*`` is ignored.

        >>> from weblinking import Link
        >>> Link("/a", [("rel", "next  last"), ("rel", "up")]).rel
        'next  last'
        """
        return self.params.get("rel")

    @property
    def rels(self) -> tuple[str, ...]:
        """The relation types of ``rel``, ASCII lower-cased as RFC 8288 compares them.

        Types are separated by runs of spaces and tabs (and the CR and LF that tolerant
        parsing also skips), never by other whitespace.

        >>> from weblinking import Link
        >>> Link("/a", {"rel": "Next  last"}).rels
        ('next', 'last')
        """
        return tuple(normalise_rel(rel) for rel in SPACES.split(self.rel or "") if rel)

    def has_rel(self, relation_type: str) -> bool:
        """True when ``rels`` holds ``relation_type``, compared without ASCII case.

        >>> from weblinking import Link
        >>> Link("/a", {"rel": "next last"}).has_rel("NEXT")
        True
        """
        return normalise_rel(need_str(relation_type, "relation_type")) in self.rels

    @property
    def rev(self) -> str | None:
        """The deprecated ``rev`` value, raw.

        >>> from weblinking import Link
        >>> Link("/a", {"rev": "made"}).rev
        'made'
        """
        return self.params.get("rev")

    @property
    def anchor(self) -> str | None:
        """The first ``anchor``: the link context when it is not the resource itself.

        >>> from weblinking import Link
        >>> Link("/a", [("rel", "up"), ("anchor", "#one"), ("anchor", "#two")]).anchor
        '#one'
        """
        return self.params.get("anchor")

    @property
    def title(self) -> str | None:
        """The title, decoded from ``title*`` when present and valid, else ``title``.

        >>> from weblinking import Link
        >>> Link("/a", {"title": "Chapter", "title*": "UTF-8''Kapitel"}).title
        'Kapitel'
        """
        return self.get("title")

    @property
    def type(self) -> str | None:
        """The ``type`` hint: the media type expected at the target.

        >>> from weblinking import Link
        >>> Link("/a", {"type": "text/html"}).type
        'text/html'
        """
        return self.params.get("type")

    @property
    def media(self) -> str | None:
        """The ``media`` attribute: the media query the target is intended for.

        >>> from weblinking import Link
        >>> Link("/a", {"media": "print"}).media
        'print'
        """
        return self.params.get("media")

    @property
    def hreflang(self) -> str | None:
        """The first ``hreflang`` value.

        >>> from weblinking import Link
        >>> Link("/a", [("hreflang", "fr"), ("hreflang", "fr-CA")]).hreflang
        'fr'
        """
        return self.params.get("hreflang")

    @property
    def hreflangs(self) -> tuple[str, ...]:
        """Every ``hreflang`` value: one link may name several languages.

        >>> from weblinking import Link
        >>> Link("/a", [("hreflang", "fr"), ("hreflang", "fr-CA")]).hreflangs
        ('fr', 'fr-CA')
        """
        return tuple(self.get_all("hreflang"))
