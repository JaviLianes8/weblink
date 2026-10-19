"""RFC 3986 section 5.2 written out step by step, as an oracle for ``resolve_uri``.

Hand-written from the pseudocode of RFC 3986 sections 5.2.2 (transform references),
5.2.3 (merge paths), 5.2.4 (remove dot segments) and 5.3 (component recomposition), in
the plain quadratic form the text gives, with the component split of Appendix B. It
shares no code with the library.
"""

from __future__ import annotations

import re

APPENDIX_B = re.compile(r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?", re.S)


def split(uri: str) -> tuple[str | None, str | None, str, str | None, str | None]:
    m = APPENDIX_B.match(uri)
    assert m is not None
    return m.group(2), m.group(4), m.group(5), m.group(7), m.group(9)


def remove_dot_segments(path: str) -> str:
    inp, out = path, ""
    while inp:
        if inp.startswith("../"):
            inp = inp[3:]
        elif inp.startswith("./"):
            inp = inp[2:]
        elif inp.startswith("/./"):
            inp = "/" + inp[3:]
        elif inp == "/.":
            inp = "/"
        elif inp.startswith("/../"):
            inp = "/" + inp[4:]
            out = out[: out.rfind("/")] if "/" in out else ""
        elif inp == "/..":
            inp = "/"
            out = out[: out.rfind("/")] if "/" in out else ""
        elif inp in (".", ".."):
            inp = ""
        else:
            start = 1 if inp.startswith("/") else 0
            end = inp.find("/", start)
            end = len(inp) if end == -1 else end
            out += inp[:end]
            inp = inp[end:]
    return out


def merge(base_authority: str | None, base_path: str, path: str) -> str:
    if base_authority is not None and base_path == "":
        return "/" + path
    if "/" not in base_path:
        return path
    return base_path[: base_path.rfind("/") + 1] + path


def resolve(reference: str, base: str) -> str:
    r_scheme, r_auth, r_path, r_query, r_frag = split(reference)
    b_scheme, b_auth, b_path, b_query, _ = split(base)
    t: tuple[str | None, str | None, str, str | None]
    if r_scheme is not None:
        t = (r_scheme, r_auth, remove_dot_segments(r_path), r_query)
    elif r_auth is not None:
        t = (b_scheme, r_auth, remove_dot_segments(r_path), r_query)
    elif r_path == "":
        t = (b_scheme, b_auth, b_path, r_query if r_query is not None else b_query)
    elif r_path.startswith("/"):
        t = (b_scheme, b_auth, remove_dot_segments(r_path), r_query)
    else:
        t = (b_scheme, b_auth, remove_dot_segments(merge(b_auth, b_path, r_path)), r_query)
    scheme, authority, path, query = t
    result = ""
    if scheme is not None:
        result += scheme + ":"
    if authority is not None:
        result += "//" + authority
    result += path
    if query is not None:
        result += "?" + query
    if r_frag is not None:
        result += "#" + r_frag
    return result
