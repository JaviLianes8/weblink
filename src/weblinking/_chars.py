"""Character classes of the grammars the library follows."""

from __future__ import annotations

import re
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
# RFC 8288 compares relation types and parameter names folding ASCII letters only, so a
# look-alike such as the Kelvin sign never turns into a token character.
_ASCII_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)
# RWS of RFC 9110, plus the CR and LF that tolerant parsing also skips.
SPACES = re.compile(r"[ \t\r\n]+")
# RFC 3986 Appendix B, with groups for scheme, authority, path, query and fragment.
COMPONENTS = re.compile(r"(?:([^:/?#]+):)?(?://([^/?#]*))?([^?#]*)(?:\?([^#]*))?(?:#(.*))?", re.S)


def ascii_lower(text: str) -> str:
    return text.translate(_ASCII_LOWER)


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
    """An RFC 3986 URI-reference: its characters, escapes and component structure.

    The contents of an IP literal between brackets are not checked further.
    """
    if not all(c in URI_CHARS for c in text):
        return False
    if not all(_is_escape(text[i + 1 : i + 3]) for i, c in enumerate(text) if c == "%"):
        return False
    match = COMPONENTS.fullmatch(text)
    assert match is not None  # every group is optional, so any string matches
    scheme, authority, path, query, fragment = match.groups()
    # A colon before the first slash is only allowed after a valid scheme (path-noscheme).
    if scheme is not None and not has_scheme(scheme + ":"):
        return False
    if fragment is not None and "#" in fragment:
        return False
    if any(c in part for c in "[]" for part in (path, query or "", fragment or "")):
        return False
    return authority is None or _is_authority(authority)


def _is_authority(authority: str) -> bool:
    userinfo, _, hostport = authority.rpartition("@")
    if any(c in userinfo for c in "[]@"):
        return False
    if hostport.startswith("["):
        close = hostport.find("]")
        if close < 2 or "[" in hostport[1:close]:
            return False
        rest = hostport[close + 1 :]
    else:
        if "[" in hostport or "]" in hostport:
            return False
        _, colon, port = hostport.partition(":")
        rest = colon + port
    return rest == "" or (rest[0] == ":" and rest[1:].isdigit()) or rest == ":"


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
