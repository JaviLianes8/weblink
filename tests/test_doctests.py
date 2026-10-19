"""Every docstring example runs and prints what it shows; every public name has one.

Each example runs with the globals of its own module, as `pytest --doctest-modules` and
`doctest.testmod` run it, so an example that forgets an import fails here too.
"""

from __future__ import annotations

import doctest
import importlib
import inspect
import pkgutil

import weblinking

MODULES = [
    weblinking,
    *(
        importlib.import_module(f"weblinking.{info.name}")
        for info in pkgutil.iter_modules(weblinking.__path__)
        if info.name not in ("__main__",)
    ),
]


def test_every_docstring_example_passes() -> None:
    finder = doctest.DocTestFinder(exclude_empty=True)
    runner = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS)
    seen: set[str] = set()
    examples = 0
    for module in MODULES:
        for test in finder.find(module):
            if test.name in seen:
                continue
            seen.add(test.name)
            examples += len(test.examples)
            runner.run(test)
    assert runner.failures == 0
    assert examples >= 50


def test_every_public_name_has_a_runnable_example() -> None:
    for name in weblinking.__all__:
        obj = getattr(weblinking, name)
        if name == "REGISTERED_RELATIONS":
            # A frozenset has no docstring of its own; the package docstring shows it.
            assert f">>> from weblinking import {name}" in (weblinking.__doc__ or "")
            continue
        assert ">>>" in (inspect.getdoc(obj) or ""), name


def test_every_link_member_has_an_example() -> None:
    members = [name for name in dir(weblinking.Link) if not name.startswith("_")]
    assert len(members) == 17
    for name in members:
        assert ">>>" in (inspect.getdoc(getattr(weblinking.Link, name)) or ""), name


def test_public_classes_name_the_public_module() -> None:
    for name in ("ExtValue", "Link", "LinkError"):
        assert getattr(weblinking, name).__module__ == "weblinking", name
