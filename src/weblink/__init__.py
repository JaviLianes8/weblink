"""Parse and build the HTTP Link header (RFC 8288), typed and zero-dependency."""

from __future__ import annotations

from ._build import build
from ._errors import LinkError
from ._model import Link
from ._parse import parse

__version__ = "0.1.0"

__all__ = ["Link", "LinkError", "build", "parse"]
