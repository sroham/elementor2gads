# Changelog

All notable project changes are documented in this file. Releases use semantic versioning.

## [1.0.0] - 2026-07-19

Initial open-source release by [Elasyn](https://elasyn.com.au).

### Added

- Local conversion of Elementor form exports to the six Google Customer Match contact columns.
- Validated input heading aliases and deterministic CSV output.
- Australian email, name, phone, state, and postcode normalisation.
- Explicit postcode extraction and optional inference from a caller-supplied lookup.
- Optional SHA-256 hashing of private identifiers while leaving country and postcode unhashed.
- Safe overwrite controls, atomic output writes, summary diagnostics, and command-line entry points.
- A helper for preparing suitably licensed locality data as `suburb,state,postcode` CSV.
- Cross-platform tests, packaging, Docker support, and privacy-focused documentation.

### Security and privacy

- No customer records, full postcode dataset, or vendor upload template are bundled.
- Input, output, and hashed exports are documented as sensitive data.
