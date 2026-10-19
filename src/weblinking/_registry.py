"""Relation types registered with IANA, and how relation types compare."""

from __future__ import annotations

from ._errors import need_str

# Names from the IANA "Link Relation Types" registry
# (https://www.iana.org/assignments/link-relations/link-relations-1.csv), last updated
# 2026-06-12. tests/test_sources.py compares this set with the fetched registry.
REGISTERED_RELATIONS: frozenset[str] = frozenset(
    (
        "about",
        "acl",
        "alternate",
        "amphtml",
        "api-catalog",
        "appendix",
        "apple-touch-icon",
        "apple-touch-startup-image",
        "archives",
        "author",
        "blocked-by",
        "bookmark",
        "c2pa-manifest",
        "canonical",
        "chapter",
        "cite-as",
        "collection",
        "compression-dictionary",
        "contents",
        "convertedfrom",
        "copyright",
        "create-form",
        "current",
        "deprecation",
        "describedby",
        "describes",
        "disclosure",
        "dns-prefetch",
        "dpp",
        "duplicate",
        "edit",
        "edit-form",
        "edit-media",
        "enclosure",
        "external",
        "first",
        "geofeed",
        "glossary",
        "help",
        "hosts",
        "hub",
        "ice-server",
        "icon",
        "index",
        "intervalafter",
        "intervalbefore",
        "intervalcontains",
        "intervaldisjoint",
        "intervalduring",
        "intervalequals",
        "intervalfinishedby",
        "intervalfinishes",
        "intervalin",
        "intervalmeets",
        "intervalmetby",
        "intervaloverlappedby",
        "intervaloverlaps",
        "intervalstartedby",
        "intervalstarts",
        "item",
        "last",
        "latest-version",
        "license",
        "linkset",
        "lrdd",
        "manifest",
        "mask-icon",
        "me",
        "media-feed",
        "memento",
        "micropub",
        "modulepreload",
        "monitor",
        "monitor-group",
        "next",
        "next-archive",
        "nofollow",
        "noopener",
        "noreferrer",
        "opener",
        "openid2.local_id",
        "openid2.provider",
        "original",
        "p3pv1",
        "payment",
        "pingback",
        "preconnect",
        "predecessor-version",
        "prefetch",
        "preload",
        "prerender",
        "prev",
        "prev-archive",
        "preview",
        "previous",
        "privacy-policy",
        "profile",
        "publication",
        "rdap-active",
        "rdap-bottom",
        "rdap-down",
        "rdap-top",
        "rdap-up",
        "related",
        "replies",
        "restconf",
        "ruleinput",
        "search",
        "section",
        "self",
        "service",
        "service-desc",
        "service-doc",
        "service-meta",
        "sip-trunking-capability",
        "sponsored",
        "start",
        "status",
        "stylesheet",
        "subsection",
        "successor-version",
        "sunset",
        "tag",
        "terms-of-service",
        "timegate",
        "timemap",
        "type",
        "ugc",
        "up",
        "version-history",
        "via",
        "webmention",
        "working-copy",
        "working-copy-of",
    )
)


_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def is_registered(relation_type: str) -> bool:
    """True when ``relation_type`` is in the IANA registry, compared case-insensitively.

    Only ASCII letters fold, as for :meth:`Link.has_rel`; ``TypeError`` for a non-``str``.

    >>> is_registered("Next"), is_registered("https://example.com/rel/x")
    (True, False)
    """
    return normalise_rel(need_str(relation_type, "relation_type")) in REGISTERED_RELATIONS


def normalise_rel(relation_type: str) -> str:
    """Lower-case the ASCII letters of a relation type, the form used to compare it.

    RFC 8288 compares registered types (section 2.1.1) and extension URIs (section 2.1.2)
    case-insensitively, character by character. Only ASCII letters fold, so a look-alike
    such as the Kelvin sign never matches a "k".
    """
    return relation_type.translate(_ASCII_LOWER)
