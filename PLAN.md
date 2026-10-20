# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

core-skeleton

## Roadmap

### core-skeleton — Core FastAPI/React skeleton with auth and video job API

Status: done

Acceptance:
- FastAPI app runs with health endpoint
- React frontend builds and loads
- OIDC Keycloak auth configured (backend sessions with HttpOnly cookies)
- Video job CRUD API with SQLite persistence
- Docker compose with backend, frontend, Keycloak, PostgreSQL
- CI workflow runs backend/frontend tests

Implementation: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/core/security.py`, `backend/app/core/oidc.py`, `backend/app/models/__init__.py`, `backend/app/api/schemas.py`, `backend/app/api/deps.py`, `backend/app/api/auth.py`, `backend/app/api/jobs.py`, `backend/app/services/color_engine.py`, `backend/app/services/video_processor.py`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx`, `frontend/src/components/JobTable.tsx`, `frontend/src/components/CreateJobModal.tsx`, `frontend/src/components/Toast.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Login.tsx`, `frontend/src/pages/Settings.tsx`, `frontend/src/hooks/useAuth.tsx`, `frontend/src/hooks/useJobs.tsx`, `frontend/src/api/client.ts`, `frontend/src/types/index.ts`

Tests: `backend/tests/test_main.py`, `frontend/src/test/components.test.tsx`

### color-space-correction — Color space correction engine for video restoration

Status: done

Acceptance:
- Detect and preserve source color metadata (primaries, transfer, matrix, range, chroma location)
- Apply correct color conversion during processing/export
- Eliminate green tint from BT.709 misassignment
- Unit tests for color metadata handling

Implementation: `backend/app/services/color_engine.py`

Tests: `backend/tests/test_main.py::TestColorEngine`

### pause-resume-jobs — Pause/resume and skip-completed video jobs

Status: done

Acceptance:
- Job checkpointing at frame boundaries
- Resume from last completed frame
- Skip already-processed files in queue
- Frontend pause/resume/skip controls

Implementation: `backend/app/services/video_processor.py`, `backend/app/api/jobs.py (pause/resume/cancel endpoints)`, `frontend/src/components/JobTable.tsx (pause/resume/cancel buttons)`

Tests: `backend/tests/test_main.py::TestVideoProcessor`, `backend/tests/test_main.py::TestJobs::test_pause_job`, `backend/tests/test_main.py::TestJobs::test_resume_job`, `backend/tests/test_main.py::TestJobs::test_cancel_job`

### mosaic-grid-artifact-fix — Fix grid pattern artifact in VR180 mosaic removal

Status: planned

Acceptance:
- Detect grid artifact in SBS+Fisheye mode
- Apply spatial filtering to suppress grid
- Preserve detail in non-mosaic areas
- Visual regression test with sample frames

### ltx-protected-inference — LTX protected inference with fallback

Status: planned

Acceptance:
- Protected worker loads LTX model safely
- Graceful fallback on protection errors
- Clear error messages for driver/environment issues

### machine-identity-fallback — Machine identity derivation with OEM fallback

Status: planned

Acceptance:
- Primary: SMBIOS UUID + board/BIOS serial
- Fallback: Windows MachineGuid registry
- Warning instead of hard failure on unsafe identity
- License validation works on OEM machines

