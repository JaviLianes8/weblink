"""Command line: print the links of a Link header, or of a whole response head, as JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from typing import TextIO

from ._errors import LinkError
from ._parse import parse

_FIELD = re.compile(r"link[ \t]*:(.*)", re.IGNORECASE)


def main(
    argv: Sequence[str] | None = None, stdin: TextIO | None = None, stdout: TextIO | None = None
) -> int:
    """Run the ``weblink`` command and return its exit status."""
    parser = argparse.ArgumentParser(
        prog="weblink",
        description="Print the links of a Link header as JSON. Without HEADER, read standard "
        "input: either a bare header value or a response head such as `curl -sI URL` prints.",
    )
    parser.add_argument("header", nargs="?", help="a Link header value")
    parser.add_argument("--base", help="resolve targets and anchors against this absolute URI")
    parser.add_argument("--strict", action="store_true", help="reject input outside RFC 8288")
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    text = args.header if args.header is not None else (stdin or sys.stdin).read()
    try:
        links = parse(field_values(text), strict=args.strict)
        if args.base is not None:
            links = [link.resolve(args.base) for link in links]
    except LinkError as error:
        print(f"weblink: {error}", file=sys.stderr)
        return 2
    rows = [{"uri": link.uri, "rels": list(link.rels), "params": link.pairs} for link in links]
    json.dump(rows, out, indent=2, ensure_ascii=False)
    out.write("\n")
    return 0


def field_values(text: str) -> list[str]:
    """The Link field values of a response head, or the text itself when it has none.

    Lines that start with whitespace continue the previous field (obsolete line folding).
    """
    fields: list[list[str]] = []
    folding = False
    for line in text.splitlines():
        if folding and line[:1] in (" ", "\t"):
            fields[-1].append(line.strip())
            continue
        match = _FIELD.match(line)
        folding = match is not None
        if match is not None:
            fields.append([match.group(1).strip()])
    if not fields:
        return [" ".join(line.strip() for line in text.splitlines())]
    return [" ".join(part for part in parts if part) for parts in fields]
