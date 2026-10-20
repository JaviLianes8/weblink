"""Errors raised by the library, and the checks that keep their messages short."""

from __future__ import annotations

import re

# Messages quote at most this many characters of the offending text (fewer when they
# need escapes), so a huge input never ends up whole in a log line.
_QUOTE_LIMIT = 80
_AUTHORITY_LEAD = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*://")


class LinkError(ValueError):
    """Raised for input outside the Link header grammar, with its offset when known.

    ``message`` is the reason and ``position`` the offset in the header line where
    parsing failed, or ``None`` when the error is about a value rather than a place in a
    header (building, decoding, resolving). Messages quote at most 80 characters of the
    input, and never the userinfo, the query or the fragment of a target, anchor or base
    URI.

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
    """Like :func:`quote`, with the userinfo, the query and the fragment of a URI hidden.

    They are where credentials, tokens and signatures travel, and messages end up in logs.
    The value is already known to be invalid, so its components cannot be trusted: all
    before the last ``@`` and all after the first ``?`` or ``#`` is hidden.
    """
    cut = min((i for i in (text.find("?"), text.find("#")) if i >= 0), default=len(text))
    at = text.rfind("@")
    if at < 0:
        shown = text[:cut]
    else:
        # Only a scheme followed by an authority is kept, never a lone "name:" prefix,
        # which may be a user name.
        lead = _AUTHORITY_LEAD.match(text)
        shown = "" if lead is None else lead.group()
        if at > cut:
            return quote(shown + "***")
        shown += "***@" + text[at + 1 : cut]
    if cut < len(text):
        shown += text[cut] + ("***" if cut + 1 < len(text) else "")
    return quote(shown)


def need_str(value: object, what: str) -> str:
    """``value`` as a plain ``str``, or ``TypeError`` naming ``what`` it was meant to be."""
    if not isinstance(value, str):
        raise TypeError(f"{what} must be str, not {type(value).__name__}")
    return str.__str__(value)
