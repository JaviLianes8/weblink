"""RFC 3986 section 5 reference resolution."""

from __future__ import annotations

import re

from ._chars import COMPONENTS, has_scheme
from ._errors import LinkError, need_str, quote

# RFC 3986 Appendix B without the scheme group.
_NO_SCHEME = re.compile(r"(?://([^/?#]*))?([^?#]*)(?:\?([^#]*))?(?:#(.*))?", re.S)
_Parts = tuple[str | None, str | None, str, str | None, str | None]


def resolve_uri(reference: str, base: str) -> str:
    """Resolve a URI reference against an absolute base URI (RFC 3986 section 5.2).

    The strict algorithm is used: a reference with a scheme is never treated as
    relative, so ``http:g`` stays ``http:g``. Text before the first colon that is not a
    scheme (a letter, then letters, digits, ``+``, ``-`` or ``.``) does not make one: such
    a reference is read as a relative path. The result is not normalised further
    (case and percent escapes are kept). Raises :class:`LinkError` when ``base`` has no
    scheme, since only an absolute URI can serve as a base, and ``TypeError`` when an
    argument is not a ``str``.

    >>> resolve_uri("../g?y#s", "http://a/b/c/d;p?q")
    'http://a/b/g?y#s'
    >>> resolve_uri("http:g", "http://a/b/c/d;p?q")
    'http:g'
    """
    reference = need_str(reference, "reference")
    base = absolute_base(base)
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


def absolute_base(base: object) -> str:
    """``base`` as a plain ``str`` once it is known to start with a scheme."""
    base = need_str(base, "base")
    if not has_scheme(base):
        raise LinkError(f"base {quote(base)} is not an absolute URI")
    return base


def _split(uri: str) -> _Parts:
    match = COMPONENTS.fullmatch(uri)
    assert match is not None  # every group is optional, so any string matches
    scheme, authority, path, query, fragment = match.groups()
    if scheme is not None and not has_scheme(scheme + ":"):
        # Not a URI reference; reading the colon as a scheme would return it unresolved.
        match = _NO_SCHEME.fullmatch(uri)
        assert match is not None
        authority, path, query, fragment = match.groups()
        return None, authority, path, query, fragment
    return scheme, authority, path, query, fragment


def _merge(base_authority: str | None, base_path: str, path: str) -> str:
    if base_authority is not None and base_path == "":
        return "/" + path
    return base_path[: base_path.rfind("/") + 1] + path


def _remove_dot_segments(path: str) -> str:
    # Section 5.2.4 with the input buffer held as ``lead + path[i:]`` instead of being
    # re-sliced at every step, so a long path costs linear time.
    out: list[str] = []
    lead, i, n = "", 0, len(path)
    while lead or i < n:
        head = lead + path[i : i + 4]
        size = len(lead) + n - i
        if head.startswith(("../", "./")):
            lead, i = "", i + len(head.split("/", 1)[0]) + 1 - len(lead)
        elif head.startswith("/./") or (size == 2 and head == "/."):
            lead, i = "/", i + min(size, 3) - len(lead)
        elif head.startswith("/../") or (size == 3 and head == "/.."):
            lead, i = "/", i + min(size, 4) - len(lead)
            if out:
                out.pop()
        elif size <= 2 and head in (".", ".."):
            lead, i = "", n
        else:
            start = i + 1 if not lead and path[i] == "/" else i
            end = path.find("/", start)
            end = n if end == -1 else end
            out.append(lead + path[i:end])
            lead, i = "", end
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
