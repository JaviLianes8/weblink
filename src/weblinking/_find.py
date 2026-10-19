"""Pick links by relation type."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from ._errors import need_str
from ._model import Link
from ._registry import normalise_rel


def find_all(links: Iterable[Link], relation_type: str) -> list[Link]:
    """Every link carrying ``relation_type``, in order (see :meth:`Link.has_rel`).

    >>> from weblinking import find_all, parse
    >>> links = parse('</1>; rel="prev first", </3>; rel=next, </9>; rel=last')
    >>> [link.uri for link in find_all(links, "FIRST")]
    ['/1']
    """
    return list(_matching(links, relation_type))


def find(links: Iterable[Link], relation_type: str) -> Link | None:
    """The first link carrying ``relation_type``, or ``None``.

    Relation types compare without ASCII case. ``TypeError`` is raised when
    ``relation_type`` is not a ``str`` or an item of ``links`` is not a :class:`Link`.

    >>> from weblinking import find, parse
    >>> find(parse('<https://api.test/?page=2>; rel="next"'), "next").uri
    'https://api.test/?page=2'
    >>> find(parse('<https://api.test/?page=2>; rel="next"'), "prev") is None
    True
    """
    return next(_matching(links, relation_type), None)


def _matching(links: Iterable[Link], relation_type: str) -> Iterator[Link]:
    wanted = normalise_rel(need_str(relation_type, "relation_type"))
    for link in links:
        if not isinstance(link, Link):
            raise TypeError(f"links must hold Link objects, not {type(link).__name__}")
        if wanted in link.rels:
            yield link
