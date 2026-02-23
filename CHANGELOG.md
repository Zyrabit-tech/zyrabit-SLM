# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `zyrabit-brain-api/README_EN.md` as the English mirror for backend documentation.
- Setup script role notes in root docs to clarify `install.sh` and `zyra-up.sh` responsibilities.

### Changed
- Updated `README.md` and `README_EN.md` to document the official setup flow.
- Updated `zyrabit-brain-api/README.md` with a link to the English version and setup script roles.
- Updated `llms-full.md` to describe bootstrap flow (`install.sh` -> `zyra-up.sh install`).

### Fixed
- Removed fixed `DOCKER_API_VERSION=1.41` from `traefik` in `zyrabit-brain-api/docker-compose.yml` to avoid Docker API compatibility errors with newer Docker engines.

### Removed
- Removed legacy `setup_slm.sh` to eliminate duplicate setup paths and reduce operational drift.

## [1.0.0-beta] - 2026-02-23

### Added
- Initial beta release baseline.
