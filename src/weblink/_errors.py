"""Errors raised by the library."""

from __future__ import annotations


class LinkError(ValueError):
    """Raised for input outside the Link header grammar, with its offset when known.

    ``position`` is the offset in the header line where parsing failed, or ``None`` when
    the error is about a value rather than a place in a header (building, decoding).
    """

    def __init__(self, message: str, position: int | None = None) -> None:
        text = message if position is None else f"{message} (offset {position})"
        super().__init__(text)
        self.message = message
        self.position = position
