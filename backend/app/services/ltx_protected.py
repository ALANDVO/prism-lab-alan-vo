"""Protected LTX model inference with graceful fallback."""

import logging
from typing import Optional, Any, Dict, Union
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class LTXModelInfo:
    """Information about LTX model loading state."""
    loaded: bool = False
    model: Optional[Any] = None
    error: Optional[str] = None
    fallback_used: bool = False
    protection_error: Optional[str] = None


class LTXProtectionError(Exception):
    """Raised when LTX model protection check fails."""
    pass


class LTXEnvironmentError(LTXProtectionError):
    """Raised when LTX environment/driver check fails."""
    pass


class LTXModelNotAvailableError(LTXProtectionError):
    """Raised when LTX model is not available."""
    pass


class ProtectedLTXWorker:
    """
    Protected worker that loads LTX model safely with graceful fallback.

    Handles:
    - Driver/environment validation before model loading
    - Graceful degradation when model unavailable
    - Clear error messages for debugging
    - Fallback to safe defaults or disabled state
    """

    def __init__(self, model_name: str = "ltx-video", strict: bool = True):
        self.model_name = model_name
        self.strict = strict
        self.info = LTXModelInfo()
        self._fallback_model: Optional[Any] = None

    def validate_environment(self) -> bool:
        """
        Validate that the environment supports LTX model loading.

        Checks:
        - Required drivers available
        - Minimum hardware requirements
        - Dependency versions
        - System configuration

        Returns:
            True if environment is valid, False otherwise

        Raises:
            LTXEnvironmentError: If environment check fails with details
        """
        try:
            # Check for torch/nn availability
            import torch
            self.info.fallback_used = False

            # Check CUDA availability if strict
            if self.strict:
                if not torch.cuda.is_available():
                    raise LTXEnvironmentError(
                        "CUDA not available; LTX model requires CUDA GPU"
                    )

            # Check for required LTX dependencies
            try:
                import ltx
                # Verify minimum version
                if hasattr(ltx, '__version__'):
                    from packaging import version
                    min_ver = "0.4.0"
                    if version.parse(ltx.__version__) < version.parse(min_ver):
                        raise LTXEnvironmentError(
                            f"LTX version {ltx.__version__} too old; minimum {min_ver} required"
                        )
            except ImportError:
                raise LTXEnvironmentError(
                    "LTX package not installed; install with: pip install ltx"
                )

            # Check for ffmpeg/ffprobe if needed for video I/O
            import shutil
            if not shutil.which("ffmpeg"):
                raise LTXEnvironmentError(
                    "ffmpeg not found in PATH; required for video I/O"
                )

            logger.info("LTX environment validation passed")
            return True

        except LTXEnvironmentError:
            raise
        except Exception as e:
            raise LTXEnvironmentError(f"Environment validation failed: {e}")

    def safe_load_model(self) -> LTXModelInfo:
        """
        Attempt to load LTX model with graceful fallback.

        Strategy:
        1. Validate environment first
        2. Attempt model import/load
        3. On failure, set error info and mark fallback as used
        4. Never raise; always return info object

        Returns:
            LTXModelInfo with loading state
        """
        self.info = LTXModelInfo()

        try:
            # Step 1: Validate environment
            self.validate_environment()

            # Step 2: Attempt to load model
            try:
                import ltx
                from ltx import LTXVideo

                # Attempt model initialization
                self.info.model = LTXVideo.from_pretrained(self.model_name)
                self.info.loaded = True
                self.info.error = None
                logger.info(f"LTX model '{self.model_name}' loaded successfully")
                return self.info

            except ImportError as e:
                # Model package not available - use fallback
                self.info.protection_error = f"Model package unavailable: {e}"
                self.info.fallback_used = True
                self._use_fallback()
                logger.warning(f"LTX model load failed (fallback): {e}")
                return self.info

            except Exception as e:
                # Load failed - use fallback
                self.info.protection_error = str(e)
                self.info.fallback_used = True
                self._use_fallback()
                logger.warning(f"LTX model load failed (fallback): {e}")
                return self.info

        except LTXEnvironmentError as e:
            # Environment check failed - use fallback without model load
            self.info.protection_error = str(e)
            self.info.fallback_used = True
            self._use_fallback()
            logger.error(f"LTX environment error (fallback): {e}")
            return self.info

        except Exception as e:
            # Unexpected error - use fallback
            self.info.protection_error = f"Unexpected error: {e}"
            self.info.fallback_used = True
            self._use_fallback()
            logger.error(f"LTX unexpected error (fallback): {e}")
            return self.info

    def _use_fallback(self) -> None:
        """Use safe fallback state instead of the LTX model."""
        self.info.fallback_used = True
        self.info.model = None
        # Set a safe fallback indicator; in production this could load
        # a lightweight alternative or disable LTX features
        self.info.error = "LTX model unavailable; using safe fallback mode"
        logger.info("Using LTX fallback mode")

    def is_available(self) -> bool:
        """Check if LTX model loaded successfully."""
        return self.info.loaded and self.info.model is not None

    def is_fallback(self) -> bool:
        """Check if fallback mode is active."""
        return self.info.fallback_used

    def get_error(self) -> Optional[str]:
        """Get the last error message, if any."""
        return self.info.protection_error or self.info.error

    def get_model(self) -> Optional[Any]:
        """Get the loaded model, or None if not available."""
        return self.info.model if self.info.loaded else None


def create_protected_ltx_worker(
    model_name: str = "ltx-video",
    strict: bool = True,
) -> ProtectedLTXWorker:
    """Factory function to create a ProtectedLTXWorker instance."""
    return ProtectedLTXWorker(model_name=model_name, strict=strict)

# Integration with video processor
from backend.app.services.video_processor import video_processor as _vp

# Protected worker instance for video jobs
protected_ltx_worker = None  # Initialized per-job in process_job


def init_protected_ltx_worker(job_id: int, model_name: str = "ltx-video", strict: bool = True):
    """Initialize a protected LTX worker for a specific job."""
    from backend.app.services.ltx_protected import ProtectedLTXWorker
    worker = ProtectedLTXWorker(model_name=model_name, strict=strict)
    worker.safe_load_model()  # Attempt load, handle fallback gracefully
    return worker


def get_protected_ltx_worker() -> Optional[ProtectedLTXWorker]:
    """Get the current protected LTX worker instance."""
    return protected_ltx_worker
