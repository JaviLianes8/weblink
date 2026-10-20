"""Contracts for the findings of the third round of independent QA on 1.0.0."""

from __future__ import annotations

from collections import namedtuple

import pytest

from weblinking import Link, LinkError, build

SECRET = "hunter2SECRET"


@pytest.mark.parametrize(
    ("target", "shown"),
    [
        # The part after the host stops at the query, even behind a userinfo.
        (f"https://alice:pw@h/ p?token={SECRET}", "'https://***@h/ p?***'"),
        # The earlier of '?' and '#' starts the hidden tail.
        (f"/x y?tok={SECRET}#frag", "'/x y?***'"),
        (f"/x y#frag?tok={SECRET}", "'/x y#***'"),
        # A mark at the very start hides everything after it.
        (f"?token={SECRET} x", "'?***'"),
        (f"#tok={SECRET} x", "'#***'"),
        # Everything before the last '@' is hidden, not only before the first.
        (f"https://alice@b:{SECRET}@h/ p", "'https://***@h/ p'"),
        # A scheme is kept only when it starts the value.
        (f"alice:{SECRET}-https://x@h/ p", "'***@h/ p'"),
        (f"alice:{SECRET}/https://x@h/ p", "'***@h/ p'"),
        # Schemes may hold digits.
        (f"h2c://alice:{SECRET}@h/ p", "'h2c://***@h/ p'"),
        # An '@' at the start still marks a userinfo, empty as it is.
        ("@h/ p", "'***@h/ p'"),
    ],
)
def test_redacted_targets_show_exactly_the_safe_parts(target: str, shown: str) -> None:
    with pytest.raises(LinkError) as caught:
        build([Link(target, {"rel": "next"})])
    message = str(caught.value)
    assert SECRET not in message
    assert "alice" not in message
    assert f"target {shown} " in message


def test_tuple_subclass_pairs_are_accepted() -> None:
    Pair = namedtuple("Pair", "name value")
    assert Link("/a", [Pair("rel", "next")]).pairs == (("rel", "next"),)
