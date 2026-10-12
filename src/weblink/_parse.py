"""Parse a Link header into a list of links, tolerant of malformed input."""

from __future__ import annotations

from ._model import Link

_WHITESPACE = " \t\r\n"
_SEPARATORS = _WHITESPACE + ","
_TOKEN_STOP = set(_WHITESPACE + ';,="')


def parse(header: str) -> list[Link]:
    """Parse an RFC 8288 ``Link`` header value into a list of :class:`Link`.

    Commas inside quoted parameter values and inside angle bracketed URIs do not
    split links. Segments that cannot be read are skipped rather than raising.
    """
    links: list[Link] = []
    i, n = 0, len(header)
    while i < n:
        i = _skip(header, i, _SEPARATORS)
        if i >= n:
            break
        if header[i] != "<":
            i = _skip_to_next_link(header, i)
            continue
        uri, i = _read_uri(header, i)
        if uri is None:
            break
        params, i = _read_params(header, i)
        links.append(Link(uri, params))
    return links


def _read_uri(s: str, i: int) -> tuple[str | None, int]:
    end = s.find(">", i + 1)
    if end == -1:
        return None, len(s)
    return s[i + 1 : end], end + 1


def _read_params(s: str, i: int) -> tuple[dict[str, str], int]:
    params: dict[str, str] = {}
    n = len(s)
    while i < n:
        i = _skip(s, i, _WHITESPACE)
        if i >= n or s[i] == ",":
            break
        if s[i] != ";":
            i = _skip_to_next_link(s, i)
            break
        i = _skip(s, i + 1, _WHITESPACE)
        name, i = _read_token(s, i)
        if not name:
            continue
        i = _skip(s, i, _WHITESPACE)
        if i < n and s[i] == "=":
            value, i = _read_value(s, _skip(s, i + 1, _WHITESPACE))
        else:
            value = ""
        key = name.lower()
        if key not in params:
            params[key] = value
    return params, i


def _read_value(s: str, i: int) -> tuple[str, int]:
    if i < len(s) and s[i] == '"':
        return _read_quoted(s, i)
    return _read_token(s, i)


def _read_token(s: str, i: int) -> tuple[str, int]:
    start, n = i, len(s)
    while i < n and s[i] not in _TOKEN_STOP:
        i += 1
    return s[start:i], i


def _read_quoted(s: str, i: int) -> tuple[str, int]:
    i += 1
    n = len(s)
    out: list[str] = []
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n:
            out.append(s[i + 1])
            i += 2
            continue
        if c == '"':
            return "".join(out), i + 1
        out.append(c)
        i += 1
    return "".join(out), i


def _skip(s: str, i: int, chars: str) -> int:
    n = len(s)
    while i < n and s[i] in chars:
        i += 1
    return i


def _skip_to_next_link(s: str, i: int) -> int:
    n = len(s)
    while i < n:
        c = s[i]
        if c == '"':
            _, i = _read_quoted(s, i)
        elif c == "<":
            end = s.find(">", i + 1)
            i = n if end == -1 else end + 1
        elif c == ",":
            return i
        else:
            i += 1
    return i
