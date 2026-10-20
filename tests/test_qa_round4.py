"""Contracts for the findings of the fourth round of independent QA on 1.0.0."""

from __future__ import annotations

import pytest

from weblinking import Link, LinkError, build

SECRET = "hunter2SECRET"


@pytest.mark.parametrize(
    ("target", "shown"),
    [
        # The hidden tail starts at the first '?' or '#', not at a later one.
        (f"/x y?tok={SECRET}?b", "'/x y?***'"),
        (f"/x y#tok={SECRET}#b", "'/x y#***'"),
        # Every scheme character is kept, in either case.
        (f"svn+ssh://alice:{SECRET}@h/ p", "'svn+ssh://***@h/ p'"),
        (f"a.b://alice:{SECRET}@h/ p", "'a.b://***@h/ p'"),
        (f"x-y://alice:{SECRET}@h/ p", "'x-y://***@h/ p'"),
        (f"HTTPS://alice:{SECRET}@h/ p", "'HTTPS://***@h/ p'"),
        # RFC 3986 allows a scheme of a single letter.
        (f"a://alice:{SECRET}@h/ p", "'a://***@h/ p'"),
        (f"Z://alice:{SECRET}@h/ p", "'Z://***@h/ p'"),
        # A scheme cannot start with a digit, so such a lead is hidden with the userinfo.
        (f"1x://alice:{SECRET}@h/ p", "'***@h/ p'"),
        # An '@' right after the mark is part of the hidden tail.
        ("/x y?@h", "'***'"),
    ],
)
def test_redacted_targets_show_exactly_the_safe_parts(target: str, shown: str) -> None:
    with pytest.raises(LinkError) as caught:
        build([Link(target, {"rel": "next"})])
    message = str(caught.value)
    assert SECRET not in message
    assert "alice" not in message
    assert f"target {shown} " in message
