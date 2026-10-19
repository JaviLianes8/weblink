"""Errors raised by the library, and the checks that keep their messages short."""

from __future__ import annotations

from ._chars import COMPONENTS

# Messages quote at most this many characters of the offending text (fewer when they
# need escapes), so a huge input never ends up whole in a log line.
_QUOTE_LIMIT = 80


class LinkError(ValueError):
    """Raised for input outside the Link header grammar, with its offset when known.

    ``message`` is the reason and ``position`` the offset in the header line where
    parsing failed, or ``None`` when the error is about a value rather than a place in a
    header (building, decoding, resolving). Messages quote at most 80 characters of the
    input, and never the userinfo or the query of a target, anchor or base URI.

    >>> error = LinkError("expected '<' to start a link", 0)
    >>> str(error), error.message, error.position
    ("expected '<' to start a link (offset 0)", "expected '<' to start a link", 0)
    >>> isinstance(error, ValueError)
    True
    """

    def __init__(self, message: str, position: int | None = None) -> None:
        text = message if position is None else f"{message} (offset {position})"
        super().__init__(text)
        self.message = message
        self.position = position


def quote(text: str) -> str:
    """The repr of ``text``, cut once its escaped form passes the limit."""
    shown = size = 0
    for c in text[: _QUOTE_LIMIT + 1]:
        # A control character or a lone surrogate takes up to ten characters escaped.
        size += len(repr(c)) - 2
        if size > _QUOTE_LIMIT:
            break
        shown += 1
    if shown == len(text):
        return repr(text)
    return f"{text[:shown]!r}... ({len(text)} characters)"


def quote_uri(text: str) -> str:
    """Like :func:`quote`, with the userinfo and the query of a URI-shaped value hidden.

    They are where credentials, tokens and signatures travel, and messages end up in logs.
    """
    match = COMPONENTS.fullmatch(text)
    assert match is not None  # every group is optional, so any string matches
    scheme, authority, path, query, fragment = match.groups()
    shown = "" if scheme is None else f"{scheme}:"
    if authority is not None:
        host = authority.rpartition("@")[2]
        shown += "//" + (f"***@{host}" if "@" in authority else host)
    shown += path
    if query is not None:
        shown += "?***" if query else "?"
    if fragment is not None:
        shown += "#" + fragment
    return quote(shown)


def need_str(value: object, what: str) -> str:
    """``value`` as a plain ``str``, or ``TypeError`` naming ``what`` it was meant to be."""
    if not isinstance(value, str):
        raise TypeError(f"{what} must be str, not {type(value).__name__}")
    return str.__str__(value)
