"""The web link value object."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Link:
    """A single web link: a target URI reference and its parameters."""

    uri: str
    params: dict[str, str] = field(default_factory=dict)

    @property
    def rel(self) -> str | None:
        """The raw ``rel`` value, which may hold several space separated tokens."""
        return self.params.get("rel")

    @property
    def rels(self) -> tuple[str, ...]:
        """The ``rel`` value split into its individual relation types."""
        rel = self.params.get("rel")
        return tuple(rel.split()) if rel else ()

    @property
    def title(self) -> str | None:
        return self.params.get("title")

    @property
    def type(self) -> str | None:
        return self.params.get("type")

    @property
    def hreflang(self) -> str | None:
        return self.params.get("hreflang")
