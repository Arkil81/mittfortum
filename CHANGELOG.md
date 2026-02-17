# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

## [3.2.0] - 2026-02-17

### Added
- Major statistics feature to:
 - Increase data gathering resolution to support 15-minute metering.
 - Create two new statistics entities to properly show hourly consumption in Energy dashboard.
 - Pull previous days data when it becomes available (every day after 15:00, retries every 30min)

## [3.1.1] - 2026-02-16

### Added
- Add NO localization and tests to fix issue #13

## [3.1.0] - 2026-02-16

### Added
- Merge locale feature from https://github.com/Hegyusz/omafortum to support FI locale
- Added tests for locales

## [3.0.1] - 2026-02-15

### Fixed
- Incorrect ID token after Fortum API changes

## [3.0.0] - 2025-05-29

### Added
- Complete refactoring of the integration architecture
- Modern Home Assistant patterns with coordinators and proper device/entity structure
- Comprehensive type safety with data models and type annotations
- Enhanced OAuth2 authentication with PKCE implementation
- Modular API client architecture with separate auth and client modules
- Custom exception hierarchy for better error handling
- Comprehensive test suite with unit and integration tests
- Development tooling with pre-commit hooks, type checking, and code formatting
- CI/CD pipeline with GitHub Actions
- Enhanced documentation with architecture details

### Changed
- **BREAKING**: Complete restructure of integration files
- **BREAKING**: Updated manifest.json to version 3.0.0
- **BREAKING**: Changed from monolithic to modular architecture
- Improved sensor separation with dedicated energy and cost sensors
- Enhanced error handling and logging
- Updated dependencies and requirements

### Fixed
- Improved OAuth2 token management and refresh logic
- Better error handling for API failures
- Enhanced data validation and type safety

### Removed
- Legacy monolithic API client
- Old OAuth2 implementation without PKCE
- Outdated sensor implementations

## [2.1.0] - 2024-12-15

### Added
- Initial OAuth2 authentication support
- Basic energy consumption monitoring
- Cost tracking functionality

### Changed
- Improved API error handling
- Updated Home Assistant compatibility

### Fixed
- Authentication token refresh issues
- Data parsing errors

## [2.0.0] - 2024-06-01

### Added
- Home Assistant integration
- Basic MittFortum API integration
- Energy consumption sensors

### Changed
- Complete rewrite from scratch
- Modern Home Assistant architecture

## [1.0.0] - 2024-01-15

### Added
- Initial release
- Basic MittFortum API client
- Simple energy monitoring
