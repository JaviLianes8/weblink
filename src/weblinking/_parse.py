"""Parse Link header lines into links, leniently or against the RFC 8288 grammar."""

from __future__ import annotations

from collections.abc import Iterable

from ._chars import LENIENT_WS, OWS, is_qdtext, is_quoted_pair_char, is_token
from ._check import check_link
from ._errors import LinkError
from ._model import Link

# A parameter name ends at whitespace, "=", ";" or "," (RFC 8288 Appendix B.3 step 5).
_NAME_STOP = frozenset(LENIENT_WS + "=;,")


def parse(header: str | Iterable[str], *, strict: bool = False) -> list[Link]:
    """Parse ``Link`` header field values into a list of :class:`Link`.

    ``header`` is one field value or an iterable of them (one per header line); a list
    never continues across lines. By default parsing is tolerant: a link that cannot be
    read is skipped up to the next comma, so it does not hide the links after it. An
    unclosed quoted value runs to the end of its line, as in RFC 8288 Appendix B.4.

    With ``strict=True`` input outside the RFC 8288 grammar raises :class:`LinkError`
    (a registered relation type is accepted in any case), as do a missing or repeated
    ``rel``, a repeated ``media``, ``title``, ``title*`` or ``type``, relation types that
    are neither registered nor ``reg-rel-type`` nor absolute URIs, targets and anchors
    that are not URI references, and starred values that are not RFC 8187 ext-values.
    Its ``position`` is the offset in the failing line.
    """
    if isinstance(header, (bytes, bytearray)):
        raise TypeError("header must be str or an iterable of str, not bytes; decode it first")
    lines = [header] if isinstance(header, str) else list(header)
    links: list[Link] = []
    for line in lines:
        if not isinstance(line, str):
            raise TypeError(f"header lines must be str, not {type(line).__name__}")
        links.extend(_Line(line, strict).links())
    return links


class _Line:
    def __init__(self, text: str, strict: bool) -> None:
        self.s = text
        self.strict = strict
        self.ws = OWS if strict else LENIENT_WS

    def fail(self, message: str, position: int) -> None:
        if self.strict:
            raise LinkError(message, position)

    def skip(self, i: int, chars: str) -> int:
        while i < len(self.s) and self.s[i] in chars:
            i += 1
        return i

    def links(self) -> list[Link]:
        s, i = self.s, 0
        out: list[Link] = []
        while True:
            i = self.skip(i, self.ws + ",")
            if i >= len(s):
                return out
            start = i
            if s[i] != "<":
                self.fail("expected '<' to start a link", i)
                i = self.resync(i)
                continue
            end = s.find(">", i + 1)
            if end == -1:
                self.fail("unclosed '<'", i)
                return out
            pairs, i = self.params(end + 1)
            link = Link(s[start + 1 : end], pairs)
            if self.strict:
                try:
                    check_link(link)
                except LinkError as error:
                    raise LinkError(error.message, start) from None
            out.append(link)

    def params(self, i: int) -> tuple[list[tuple[str, str]], int]:
        s = self.s
        pairs: list[tuple[str, str]] = []
        while True:
            i = self.skip(i, self.ws)
            if i >= len(s) or s[i] == ",":
                return pairs, i
            if s[i] != ";":
                self.fail("expected ';' or ','", i)
                return pairs, self.resync(i)
            i = self.skip(i + 1, self.ws)
            start = i
            while i < len(s) and s[i] not in _NAME_STOP:
                i += 1
            name = s[start:i]
            if not is_token(name):
                self.fail("expected a parameter name", start)
            i = self.skip(i, self.ws)
            value = ""
            if i < len(s) and s[i] == "=":
                i = self.skip(i + 1, self.ws)
                if i < len(s) and s[i] == '"':
                    if name.endswith("*"):
                        self.fail("an RFC 8187 value cannot be quoted", i)
                    value, i = self.quoted(i)
                else:
                    value, i = self.bare(i)
            if name:
                pairs.append((name.lower(), value))

    def bare(self, i: int) -> tuple[str, int]:
        start = i
        while i < len(self.s) and self.s[i] not in ";,":
            i += 1
        value = self.s[start:i].rstrip(self.ws)
        if not is_token(value):
            self.fail("expected a token or a quoted string", start)
        return value, i

    def quoted(self, i: int) -> tuple[str, int]:
        s, start, out = self.s, i, []
        i += 1
        while i < len(s):
            c = s[i]
            if c == "\\":
                if i + 1 >= len(s):
                    break
                if not is_quoted_pair_char(s[i + 1]):
                    self.fail("invalid character after a backslash", i + 1)
                out.append(s[i + 1])
                i += 2
                continue
            if c == '"':
                return "".join(out), i + 1
            if not is_qdtext(c):
                self.fail("invalid character in a quoted string", i)
            out.append(c)
            i += 1
        self.fail("unclosed quoted string", start)
        return "".join(out), len(s)

    def resync(self, i: int) -> int:
        # Text outside the grammar has no quoting: honouring a stray quote or bracket there
        # would let it swallow the well-formed links that follow, so the next comma wins.
        end = self.s.find(",", i)
        return len(self.s) if end == -1 else end
