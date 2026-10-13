"""RFC 3986 section 5 reference resolution."""

from __future__ import annotations

import re

from ._chars import has_scheme
from ._errors import LinkError

# RFC 3986 Appendix B, with groups for the five components.
_COMPONENTS = re.compile(r"(?:([^:/?#]+):)?(?://([^/?#]*))?([^?#]*)(?:\?([^#]*))?(?:#(.*))?", re.S)

_Parts = tuple[str | None, str | None, str, str | None, str | None]


def resolve_uri(reference: str, base: str) -> str:
    """Resolve a URI reference against an absolute base URI (RFC 3986 section 5.2).

    The strict algorithm is used: a reference with a scheme is never treated as
    relative, so ``http:g`` stays ``http:g``. Raises :class:`LinkError` when ``base``
    has no scheme, since only an absolute URI can serve as a base.
    """
    if not has_scheme(base):
        raise LinkError(f"base {base!r} is not an absolute URI")
    r_scheme, r_auth, r_path, r_query, r_frag = _split(reference)
    b_scheme, b_auth, b_path, b_query, _ = _split(base)
    if r_scheme is not None:
        return _join(r_scheme, r_auth, _remove_dot_segments(r_path), r_query, r_frag)
    if r_auth is not None:
        return _join(b_scheme, r_auth, _remove_dot_segments(r_path), r_query, r_frag)
    if r_path == "":
        query = r_query if r_query is not None else b_query
        return _join(b_scheme, b_auth, b_path, query, r_frag)
    if r_path.startswith("/"):
        path = _remove_dot_segments(r_path)
    else:
        path = _remove_dot_segments(_merge(b_auth, b_path, r_path))
    return _join(b_scheme, b_auth, path, r_query, r_frag)


def _split(uri: str) -> _Parts:
    match = _COMPONENTS.fullmatch(uri)
    assert match is not None  # every group is optional, so any string matches
    scheme, authority, path, query, fragment = match.groups()
    return scheme, authority, path, query, fragment


def _merge(base_authority: str | None, base_path: str, path: str) -> str:
    if base_authority is not None and base_path == "":
        return "/" + path
    return base_path[: base_path.rfind("/") + 1] + path


def _remove_dot_segments(path: str) -> str:
    out: list[str] = []
    while path:
        if path.startswith("../"):
            path = path[3:]
        elif path.startswith("./"):
            path = path[2:]
        elif path.startswith("/./") or path == "/.":
            path = "/" + path[3:]
        elif path.startswith("/../") or path == "/..":
            path = "/" + path[4:]
            if out:
                out.pop()
        elif path in (".", ".."):
            path = ""
        else:
            end = path.find("/", 1)
            end = len(path) if end == -1 else end
            out.append(path[:end])
            path = path[end:]
    return "".join(out)


def _join(
    scheme: str | None, authority: str | None, path: str, query: str | None, fragment: str | None
) -> str:
    out = f"{scheme}:" if scheme is not None else ""
    if authority is not None:
        out += "//" + authority
    out += path
    if query is not None:
        out += "?" + query
    if fragment is not None:
        out += "#" + fragment
    return out
