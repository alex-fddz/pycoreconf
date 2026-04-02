# Changelog

## [Unreleased]

### Added
- Datastore feature
  - Store and manipulate CORECONF configuration data
  - Use high-level abstraction with XPath-like syntax
  - Include docs and `terraforma` sample

### Changed
- API: `sid_files` accepts both list and single string path
- Require `yangson` module to enable validation by default

## Fixed
- JSON encoding for 64-bit numeric types (RFC 7951)

## [0.1.1] - 2026-03-20

### Added
- Configuration validation during encoding (raises error if invalid)
- Tests and improved API documentation
- `requirements.txt` for development and testing
- Required YANG modules for `validation` sample

### Changed
- Unified SID file loading and data extraction via `_collect_sid_data`

### Removed
- Deprecated SID single-data extractor functions

### Fixed
- Various bug fixes across serialization and validation

## [0.1.0] - 2026-03-17

### Added
- Full support for multiple YANG SID files
- New SID file format support (pyang update)

### Changed
- API: `sid_files` is now a list of paths
- Started codebase refactoring
- Identifier key reconstruction for `identityref`

### Fixed
- SID casting and consistency issues (pyang update)

## [0.0.6] - 2024-03-29

### Added
- Key mapping extraction from SID file
- Legacy SID files support

## [0.0.5] - 2024-06-27

### Added
- Non-recursive serialization functions

### Changed
- Human-readable CBOR output in hex
- Updated pyang compatibility

## [0.0.4] - 2023-05-4

### Added
- Initial release on PyPi
- Initial documentation and examples
- Support for `identityref`, `leafref`, `enum`, ...

### Changed
- Initial improvements and fixes

## [0.0.1] - 2023-03-16

### Added
- ModelSID and CORECONFModel core classes
  - Serialization to/from CORECONF (CBOR)
  - Basic validation support
