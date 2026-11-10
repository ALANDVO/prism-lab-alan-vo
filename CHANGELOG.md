# Changelog

## 1.3.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

### Added (this round)
- Mosaic grid artifact detection and filtering for VR180 video restoration (`mosaic-grid-artifact-fix`)
  - New `MosaicGridFilter` service with frequency-domain grid detection using FFT analysis
  - Supports SBS fisheye, TB fisheye, and mono fisheye VR180 modes
  - Spatial filtering with bilateral filter to suppress grid while preserving detail
  - Factory function with mode-specific detection thresholds and filter strengths
  - Integration into video processor job pipeline
- Comprehensive test suite for mosaic filter (13 tests)

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-10-20

### Added
- Initial release of prism-lab-alan-vo
- FastAPI backend with SQLite persistence
- React + TypeScript + Vite frontend
- OIDC Keycloak authentication with PKCE
- Video job CRUD API with pagination and filtering
- Color metadata extraction and preservation engine
- Job checkpointing for pause/resume capability
- Docker Compose with backend, frontend, Keycloak
- CI/CD pipeline with backend and frontend tests

### AI/ML Features
- Color space correction engine to prevent green tint artifacts (addresses BT.709 misassignment)
- Video color metadata preservation from source files
- Deterministic offline color correction without LLM dependency

---

Alan Vo · [alanvo.net](https://alanvo.net) · [X: @alanvoasi](https://x.com/alanvoasi)
