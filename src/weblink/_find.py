"""Pick links by relation type."""

from __future__ import annotations

from collections.abc import Iterable

from ._model import Link


def find_all(links: Iterable[Link], relation_type: str) -> list[Link]:
    """Every link carrying ``relation_type``, in order (see :meth:`Link.has_rel`)."""
    return [link for link in links if link.has_rel(relation_type)]


def find(links: Iterable[Link], relation_type: str) -> Link | None:
    """The first link carrying ``relation_type``, or ``None``.

    >>> find(parse('<https://api.test/?page=2>; rel="next"'), "next").uri
    'https://api.test/?page=2'
    """
    return next((link for link in links if link.has_rel(relation_type)), None)
