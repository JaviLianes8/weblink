"""Character classes of the grammars the library follows."""

from __future__ import annotations

import string

# RFC 9110 section 5.6.2.
TCHAR = frozenset("!#$%&'*+-.^_`|~" + string.digits + string.ascii_letters)
# RFC 9110 section 5.6.3; recipients of folded or joined lines also meet CR and LF.
OWS = " \t"
LENIENT_WS = " \t\r\n"
# RFC 3986 section 2: unreserved, reserved and the percent sign of pct-encoded.
URI_CHARS = frozenset(string.ascii_letters + string.digits + "-._~:/?#[]@!$&'()*+,;=%")
SCHEME_CHARS = frozenset(string.ascii_letters + string.digits + "+-.")
# RFC 8187 section 3.2.1.
ATTR_CHARS = frozenset(string.ascii_letters + string.digits + "!#$&+-.^_`|~")
HEXDIGITS = frozenset(string.hexdigits)


def is_token(text: str) -> bool:
    return bool(text) and all(c in TCHAR for c in text)


def is_qdtext(c: str) -> bool:
    """RFC 9110 section 5.6.4: HTAB, SP, visible ASCII but quote and backslash, obs-text."""
    code = ord(c)
    return c in "\t " or (0x21 <= code <= 0x7E and c not in '"\\') or 0x80 <= code <= 0xFF


def is_quoted_pair_char(c: str) -> bool:
    code = ord(c)
    return c in "\t " or 0x21 <= code <= 0x7E or 0x80 <= code <= 0xFF


def is_uri_reference(text: str) -> bool:
    """Character-level check of an RFC 3986 URI-reference: allowed characters, valid escapes."""
    if not all(c in URI_CHARS for c in text):
        return False
    return all(_is_escape(text[i + 1 : i + 3]) for i, c in enumerate(text) if c == "%")


def _is_escape(digits: str) -> bool:
    return len(digits) == 2 and set(digits) <= HEXDIGITS


def has_scheme(text: str) -> bool:
    """True when ``text`` starts with an RFC 3986 scheme and a colon."""
    scheme, colon, _ = text.partition(":")
    return (
        bool(colon)
        and bool(scheme)
        and scheme[0] in string.ascii_letters
        and all(c in SCHEME_CHARS for c in scheme)
    )
