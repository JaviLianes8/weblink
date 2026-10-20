"""RFC 8187 extended parameter values, such as the one ``title*`` carries."""

from __future__ import annotations

import string
from typing import NamedTuple

from ._chars import ATTR_CHARS, HEXDIGITS
from ._errors import LinkError, need_str, quote

# UTF-8 is required by RFC 8187; ISO-8859-1 is what RFC 5987 required, and recipients are
# encouraged to keep reading it.
_CODECS = {"utf-8": ("UTF-8", "utf-8"), "iso-8859-1": ("ISO-8859-1", "latin-1")}
_LANGUAGE_CHARS = frozenset(string.ascii_letters + string.digits + "-")


class ExtValue(NamedTuple):
    """A decoded RFC 8187 value: the text, its language tag (may be empty), its charset.

    ``charset`` is ``"UTF-8"`` or ``"ISO-8859-1"`` whatever case the value used.

    >>> ExtValue("letztes Kapitel", "de", "UTF-8").language
    'de'
    """

    value: str
    language: str
    charset: str


def decode_ext_value(text: str) -> ExtValue:
    """Decode an RFC 8187 ``ext-value`` such as ``UTF-8'de'n%c3%a4chstes``.

    Charset names compare case-insensitively; only UTF-8 and ISO-8859-1 are read, so
    another charset the RFC 8187 grammar allows (``US-ASCII``) is refused, and so are
    escaped octets the charset cannot decode. The language tag is checked lightly
    (letters, digits and hyphens, not starting with a hyphen), not against RFC 5646.
    Raises :class:`LinkError` for a missing part, such a charset or language, a character
    outside ``attr-char`` or a broken percent escape; ``TypeError`` when ``text`` is not a
    ``str``.

    >>> decode_ext_value("UTF-8'de'n%c3%a4chstes%20Kapitel")
    ExtValue(value='nächstes Kapitel', language='de', charset='UTF-8')
    >>> decode_ext_value("iso-8859-1'en'%A3%20rates").value
    '£ rates'
    """
    text = need_str(text, "ext-value")
    charset, quote1, rest = text.partition("'")
    language, quote2, chars = rest.partition("'")
    if not quote1 or not quote2:
        raise LinkError(f"ext-value {quote(text)} needs the form charset'language'value")
    codec = _CODECS.get(charset.lower())
    if codec is None:
        raise LinkError(f"ext-value charset {quote(charset)} is not UTF-8 or ISO-8859-1")
    _check_language(language)
    octets = bytearray()
    i = 0
    while i < len(chars):
        c = chars[i]
        if c == "%":
            digits = chars[i + 1 : i + 3]
            if len(digits) != 2 or not set(digits) <= HEXDIGITS:
                raise LinkError(f"ext-value {quote(text)} has a broken percent escape")
            octets.append(int(digits, 16))
            i += 3
            continue
        if c not in ATTR_CHARS:
            raise LinkError(f"ext-value {quote(text)} has {c!r}, which must be percent-encoded")
        octets.append(ord(c))
        i += 1
    try:
        value = octets.decode(codec[1])
    except UnicodeDecodeError:
        raise LinkError(f"ext-value {quote(text)} is not valid {codec[0]}") from None
    return ExtValue(value, language, codec[0])


def encode_ext_value(value: str, language: str = "") -> str:
    """Encode text as an RFC 8187 ``ext-value`` in UTF-8, for ``title*`` and the like.

    Every octet outside ``attr-char`` is percent-encoded with upper-case hex digits.
    Raises :class:`LinkError` for a lone surrogate or a language that is not built from
    letters, digits and hyphens; ``TypeError`` when an argument is not a ``str``.

    >>> encode_ext_value("nächstes Kapitel", "de")
    "UTF-8'de'n%C3%A4chstes%20Kapitel"
    >>> decode_ext_value(encode_ext_value("€ rates")).value
    '€ rates'
    """
    value = need_str(value, "value")
    _check_language(need_str(language, "language"))
    try:
        octets = value.encode("utf-8")
    except UnicodeEncodeError:
        raise LinkError("text with a lone surrogate cannot be encoded as UTF-8") from None
    out = [chr(o) if chr(o) in ATTR_CHARS else f"%{o:02X}" for o in octets]
    return f"UTF-8'{language}'{''.join(out)}"


def _check_language(language: str) -> None:
    # A light check: a Language-Tag is built from letters, digits and hyphens.
    if not set(language) <= _LANGUAGE_CHARS or language.startswith("-"):
        raise LinkError(f"language tag {quote(language)} is not a Language-Tag")
