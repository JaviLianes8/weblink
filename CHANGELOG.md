# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

### Added

- `parse(..., strict=True)` checks the RFC 8288 grammar and raises `LinkError` with the
  offset: input outside the ABNF (registered relation types are accepted in any case),
  targets and anchors that are not structurally URI references, a missing or repeated `rel`, a repeated `media`,
  `title`, `title*` or `type`, malformed relation types, invalid starred values.
- `parse` takes a list of header lines; a quoted string never runs into the next line.
- RFC 8187 support: `decode_ext_value`, `encode_ext_value` and `ExtValue`; `Link.title`
  and `Link.get` prefer a decodable `title*` (or any `name*`) over the plain value.
- `resolve_uri` (RFC 3986 section 5.2, strict form), `Link.resolve` for the target and
  `anchor`, and `Link.context`.
- `Link.pairs`, `Link.get_all` and `Link.hreflangs` keep parameters that repeat.
- `Link.has_rel`, `find` and `find_all`; `REGISTERED_RELATIONS` and `is_registered` from
  the IANA registry; `Link.rev`, `Link.anchor` and `Link.media`.
- The `weblink` command (also `python -m weblink`) prints the links of a header value or
  of a response head as ASCII JSON, with `--base` and `--strict`. Standard input is read
  as ISO-8859-1 octets; in a head only `Link` fields of the final response count.

### Changed

- `Link` is immutable and hashable and keeps every parameter in order. `params` is now a
  new first-wins dict on each access, so changing it no longer changes the link.
  Parameter names are lower-cased on construction.
- `rels` lower-cases the ASCII letters of every relation type, and relation types compare
  case-insensitively, extension URIs included (RFC 8288 section 2.1.2).
- An unquoted value runs to the next `;` or `,` (RFC 8288 Appendix B.3) instead of
  stopping at a space.
- Text that cannot be read is skipped up to the next comma; quotes and brackets in it are
  no longer honoured, so a stray one cannot swallow the links that follow.
- `build` refuses a link without `rel`, control characters and non-ASCII text in values,
  targets that are not URI references, and names that are not tokens; starred values
  are written unquoted, as RFC 8187 requires. `<>` (the empty reference) is accepted.
- `bytes` input raises `TypeError` with a hint to decode it.

## [0.1.0]

- First release.
- `parse` reads an RFC 8288 `Link` header into a list of `Link` objects, handling
  quoted parameters, commas inside quoted values, multiple space separated `rel`
  values, and malformed input tolerantly.
- `build` serialises a list of `Link` objects back into a header value, quoting
  and escaping parameter values so the result round-trips through `parse`.
- `Link` exposes the target `uri`, a `params` dict, and typed accessors for
  `rel`, `rels`, `title`, `type`, and `hreflang`.
