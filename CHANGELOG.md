# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- First release.
- `parse` reads an RFC 8288 `Link` header into a list of `Link` objects, handling
  quoted parameters, commas inside quoted values, multiple space separated `rel`
  values, and malformed input tolerantly.
- `build` serialises a list of `Link` objects back into a header value, quoting
  and escaping parameter values so the result round-trips through `parse`.
- `Link` exposes the target `uri`, a `params` dict, and typed accessors for
  `rel`, `rels`, `title`, `type`, and `hreflang`.
