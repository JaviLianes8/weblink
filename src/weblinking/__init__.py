"""Parse, validate, resolve and build the HTTP Link header (RFC 8288), typed and zero-dependency.

``REGISTERED_RELATIONS`` is the frozenset of the relation type names in the IANA "Link
Relation Types" registry (as updated on 2026-06-12), all lower case.

>>> from weblinking import REGISTERED_RELATIONS, find, parse
>>> "next" in REGISTERED_RELATIONS, len(REGISTERED_RELATIONS)
(True, 134)
>>> find(parse('</items?page=3>; rel="next"'), "next").resolve("https://api.test/items").uri
'https://api.test/items?page=3'
"""

from __future__ import annotations

from ._build import build
from ._errors import LinkError
from ._ext import ExtValue, decode_ext_value, encode_ext_value
from ._find import find, find_all
from ._model import Link
from ._parse import parse
from ._registry import REGISTERED_RELATIONS, is_registered
from ._uri import resolve_uri

__version__ = "1.0.0"

# Pickles and tracebacks name the public module, so the private layout can change freely.
for _public in (ExtValue, Link, LinkError):
    _public.__module__ = __name__
del _public

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
