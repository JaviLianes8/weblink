"""Parse and build the HTTP Link header (RFC 8288), typed and zero-dependency."""

from __future__ import annotations

from ._build import build
from ._errors import LinkError
from ._ext import ExtValue, decode_ext_value, encode_ext_value
from ._find import find, find_all
from ._model import Link
from ._parse import parse
from ._registry import REGISTERED_RELATIONS, is_registered
from ._uri import resolve_uri

__version__ = "0.2.0"

__all__ = [
    "REGISTERED_RELATIONS",
    "ExtValue",
    "Link",
    "LinkError",
    "build",
    "decode_ext_value",
    "encode_ext_value",
    "find",
    "find_all",
    "is_registered",
    "parse",
    "resolve_uri",
]
