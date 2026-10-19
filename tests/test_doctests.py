"""Every docstring example runs and prints what it shows; every public name has one."""

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
        for test in finder.find(module, globs=dict(vars(weblinking))):
            if test.name in seen:
                continue
            seen.add(test.name)
            examples += len(test.examples)
            runner.run(test)
    assert runner.failures == 0
    assert examples >= 27


def test_every_public_name_has_a_runnable_example() -> None:
    for name in weblinking.__all__:
        obj = getattr(weblinking, name)
        if name == "REGISTERED_RELATIONS":
            # A frozenset has no docstring of its own; the package docstring shows it.
            assert f">>> from weblinking import {name}" in (weblinking.__doc__ or "")
            continue
        assert ">>>" in (inspect.getdoc(obj) or ""), name


def test_the_main_link_methods_have_examples() -> None:
    for name in ("get", "get_all", "has_rel", "rels", "resolve", "context"):
        assert ">>>" in (inspect.getdoc(getattr(weblinking.Link, name)) or ""), name


def test_public_classes_name_the_public_module() -> None:
    for name in ("ExtValue", "Link", "LinkError"):
        assert getattr(weblinking, name).__module__ == "weblinking", name
