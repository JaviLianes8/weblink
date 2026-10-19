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
# A response head starts with a status line or a header field name and a colon.
_HEAD = re.compile(r"HTTP/|[!#$%&'*+.^_`|~0-9A-Za-z-]+[ \t]*:")


def main(
    argv: Sequence[str] | None = None, stdin: TextIO | None = None, stdout: TextIO | None = None
) -> int:
    """Run the ``weblinking`` command and return its exit status."""
    parser = argparse.ArgumentParser(
        prog="weblinking",
        description="Print the links of a Link header as JSON. Without HEADER, read standard "
        "input: either a bare header value or a response head such as `curl -sI URL` prints.",
    )
    parser.add_argument("header", nargs="?", help="a Link header value")
    parser.add_argument("--base", help="resolve targets and anchors against this absolute URI")
    parser.add_argument("--strict", action="store_true", help="reject input outside RFC 8288")
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    if args.header is not None:
        text = args.header
    elif stdin is not None:
        text = stdin.read()
    else:
        # HTTP field values are octets; ISO-8859-1 maps each one to a character, so
        # obs-text bytes never make the command fail before parsing starts.
        text = sys.stdin.buffer.read().decode("latin-1")
    try:
        links = parse(field_values(text), strict=args.strict)
        if args.base is not None:
            links = [link.resolve(args.base) for link in links]
    except LinkError as error:
        print(f"weblinking: {error}", file=sys.stderr)
        return 2
    rows = [{"uri": link.uri, "rels": list(link.rels), "params": link.pairs} for link in links]
    # ASCII output cannot fail on a console or pipe whose encoding lacks a character.
    json.dump(rows, out, indent=2, ensure_ascii=True)
    out.write("\n")
    return 0


def field_values(text: str) -> list[str]:
    """The Link field values of a response head, or the text as one value when it is not one.

    In a head, lines that start with whitespace continue the previous field (obsolete line
    folding), a blank line ends the head, and a later status line starts a new response
    whose fields replace the earlier ones, so `curl -sIL` reports the final response.
    """
    lines = [line.removesuffix("\r") for line in text.split("\n")]
    first = next((line for line in lines if line.strip()), "")
    if not _HEAD.match(first):
        return [" ".join(line.strip() for line in lines if line.strip())]
    fields: list[list[str]] = []
    folding, in_head = False, True
    for line in lines:
        if line.startswith("HTTP/"):
            fields, folding, in_head = [], False, True
            continue
        if not in_head:
            continue
        if not line.strip():
            in_head = False
        elif folding and line[:1] in (" ", "\t") and fields:
            fields[-1].append(line.strip())
        else:
            match = _FIELD.match(line)
            folding = match is not None
            if match is not None:
                fields.append([match.group(1).strip()])
    return [" ".join(part for part in parts if part) for parts in fields]
