"""Tests for ProtectedLTXWorker protected inference with fallback."""

import pytest
from backend.app.services.ltx_protected import (
    ProtectedLTXWorker,
    create_protected_ltx_worker,
    LTXProtectionError,
    LTXEnvironmentError,
    LTXModelInfo,
)


class TestProtectedLTXWorker:
    """Tests for ProtectedLTXWorker class."""

    def test_worker_creation_default(self):
        """Test worker creation with defaults."""
        worker = create_protected_ltx_worker()
        assert worker.model_name == "ltx-video"
        assert worker.strict is True

    def test_worker_creation_custom(self):
        """Test worker creation with custom parameters."""
        worker = create_protected_ltx_worker(model_name="ltx-audio", strict=False)
        assert worker.model_name == "ltx-audio"
        assert worker.strict is False

    def test_is_available_when_not_loaded(self):
        """Test is_available returns False when model not loaded."""
        worker = create_protected_ltx_worker()
        assert worker.is_available() is False

    def test_is_fallback_when_not_attempted(self):
        """Test is_fallback returns False when not attempted."""
        worker = create_protected_ltx_worker()
        assert worker.is_fallback() is False

    def test_get_error_when_no_error(self):
        """Test get_error returns None when no error."""
        worker = create_protected_ltx_worker()
        assert worker.get_error() is None

    def test_get_model_when_not_available(self):
        """Test get_model returns None when model not available."""
        worker = create_protected_ltx_worker()
        assert worker.get_model() is None

    def test_safe_load_model_environment_failure(self):
        """Test safe_load_model handles environment failure gracefully."""
        worker = create_protected_ltx_worker(strict=True)
        result = worker.safe_load_model()
        assert result.fallback_used is True
        assert result.loaded is False
        assert result.protection_error is not None
        assert "CUDA" in result.protection_error or "environment" in result.protection_error.lower()

    def test_safe_load_model_package_missing(self):
        """Test safe_load_model handles missing package gracefully."""
        worker = create_protected_ltx_worker(strict=False)
        result = worker.safe_load_model()
        assert result.fallback_used is True
        assert result.loaded is False
        assert result.protection_error is not None

    def test_safe_load_model_success_path_isolated(self):
        """Test safe_load_model success path (isolated - may not actually load)."""
        # With strict=True and no CUDA, this will fall back; that's expected
        worker = create_protected_ltx_worker(strict=True)
        result = worker.safe_load_model()
        # Should have attempted and fallen back gracefully
        assert isinstance(result, LTXModelInfo)
        assert hasattr(result, 'loaded')
        assert hasattr(result, 'fallback_used')

    def test_protection_error_types(self):
        """Test that protection errors are proper exception types."""
        worker = create_protected_ltx_worker(strict=True)
        result = worker.safe_load_model()
        err = result.protection_error
        assert isinstance(err, str)

    def test_worker_preserves_state(self):
        """Test worker maintains consistent state after load attempt."""
        worker = create_protected_ltx_worker(strict=False)
        result1 = worker.safe_load_model()
        result2 = worker.safe_load_model()
        # Same result both times
        assert result1.fallback_used == result2.fallback_used
        assert result1.protection_error == result2.protection_error


class TestCreateProtectedLTXWorker:
    """Tests for create_protected_ltx_worker factory."""

    def test_factory_returns_worker(self):
        """Test factory returns a ProtectedLTXWorker instance."""
        worker = create_protected_ltx_worker()
        from backend.app.services.ltx_protected import ProtectedLTXWorker
        assert isinstance(worker, ProtectedLTXWorker)

    def test_factory_with_params(self):
        """Test factory accepts and forwards parameters."""
        worker = create_protected_ltx_worker(model_name="custom-ltx", strict=True)
        assert worker.model_name == "custom-ltx"
        assert worker.strict is True


class TestLTXModelInfo:
    """Tests for LTXModelInfo dataclass."""

    def test_dataclass_fields(self):
        """Test LTXModelInfo has expected fields."""
        info = LTXModelInfo(
            loaded=False,
            model=None,
            error=None,
            fallback_used=False,
            protection_error=None,
        )
        assert info.loaded is False
        assert info.model is None
        assert info.error is None
        assert info.fallback_used is False
        assert info.protection_error is None

    def test_dataclass_defaults(self):
        """Test LTXModelInfo field defaults."""
        info = LTXModelInfo()
        assert info.loaded is False
        assert info.model is None
        assert info.error is None
        assert info.fallback_used is False
        assert info.protection_error is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
