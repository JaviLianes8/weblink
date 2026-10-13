"""Checks a link against RFC 8288, shared by strict parsing and building."""

from __future__ import annotations

import re

from ._chars import has_scheme, is_token, is_uri_reference
from ._errors import LinkError
from ._ext import decode_ext_value
from ._model import Link
from ._registry import is_registered

# RFC 8288 section 3.3 reg-rel-type, compared case-insensitively (section 2.1.1).
_REG_REL_TYPE = re.compile(r"[a-z][a-z0-9.\-]*", re.IGNORECASE)
# RFC 8288 sections 3.3 and 3.4.1: these may appear once in a link-value.
_SINGLE = ("rel", "media", "title", "title*", "type")


def check_link(link: Link) -> None:
    """Raise :class:`LinkError` when ``link`` breaks the RFC 8288 rules for a link-value."""
    if not is_uri_reference(link.uri):
        raise LinkError(f"target {link.uri!r} is not a URI reference")
    names = [name for name, _ in link.pairs]
    for name in names:
        if not is_token(name):
            raise LinkError(f"parameter name {name!r} is not a token")
    for name in _SINGLE:
        if names.count(name) > 1:
            raise LinkError(f"parameter {name!r} appears more than once")
    if "rel" not in names:
        raise LinkError("a link needs a rel parameter")
    for name, value in link.pairs:
        if name in ("rel", "rev"):
            check_relation_types(name, value)
        elif name == "anchor" and not is_uri_reference(value):
            raise LinkError(f"anchor {value!r} is not a URI reference")
        elif name.endswith("*"):
            decode_ext_value(value)


def check_relation_types(name: str, value: str) -> None:
    """``relation-type *( 1*SP relation-type )`` of RFC 8288 section 3.3."""
    if not value or value != value.strip(" "):
        raise LinkError(f"{name} value {value!r} is empty or has outer spaces")
    for relation_type in value.split(" "):
        if relation_type and not _is_relation_type(relation_type):
            raise LinkError(f"{name} value {relation_type!r} is not a relation type")


def _is_relation_type(text: str) -> bool:
    if _REG_REL_TYPE.fullmatch(text) or is_registered(text):
        return True
    # An extension relation type is an absolute URI (RFC 8288 section 3.3).
    return has_scheme(text) and is_uri_reference(text)
