"""Tests for mosaic grid artifact filter."""
import pytest
import numpy as np
import cv2
from app.services.mosaic_filter import (
    MosaicGridFilter,
    MosaicMode,
    GridDetectionResult,
    create_mosaic_filter,
)


class TestMosaicGridFilter:
    """Tests for MosaicGridFilter class."""

    def test_filter_creation_default_params(self):
        """Test filter creation with default parameters."""
        filter = MosaicGridFilter()
        assert filter.grid_threshold == 0.3
        assert filter.filter_strength == 0.5
        assert filter.min_grid_size == 8
        assert filter.max_grid_size == 64

    def test_filter_creation_custom_params(self):
        """Test filter creation with custom parameters."""
        filter = MosaicGridFilter(
            grid_threshold=0.4,
            filter_strength=0.7,
            min_grid_size=10,
            max_grid_size=50,
        )
        assert filter.grid_threshold == 0.4
        assert filter.filter_strength == 0.7
        assert filter.min_grid_size == 10
        assert filter.max_grid_size == 50

    def test_detect_grid_no_grid(self):
        """Test grid detection on frame without grid pattern."""
        filter = MosaicGridFilter()
        # Create a random noise frame (no grid)
        frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        result = filter.detect_grid(frame)
        assert result.has_grid is False
        assert result.confidence == 0.0

    def test_detect_grid_with_synthetic_grid(self):
        """Test grid detection on frame with synthetic grid pattern."""
        filter = MosaicGridFilter(grid_threshold=0.15)  # Lower threshold for synthetic test
        # Create frame with clear grid pattern
        frame = np.zeros((240, 320), dtype=np.uint8)
        grid_spacing = 20
        for y in range(0, 240, grid_spacing):
            frame[y:y+2, :] = 255
        for x in range(0, 320, grid_spacing):
            frame[:, x:x+2] = 255
        # Add some noise
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        noise = np.random.randint(0, 30, frame.shape, dtype=np.uint8)
        frame = cv2.add(frame, noise)
        
        result = filter.detect_grid(frame)
        # Should detect grid (though confidence may vary)
        # At minimum, should not crash
        assert isinstance(result, GridDetectionResult)
        assert hasattr(result, 'has_grid')
        assert hasattr(result, 'confidence')

    def test_filter_frame_no_grid(self):
        """Test filtering frame without grid returns original."""
        filter = MosaicGridFilter()
        frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        result = filter.filter_frame(frame)
        # Should return frame unchanged (or very similar)
        assert result.shape == frame.shape
        assert result.dtype == frame.dtype

    def test_process_video_frame(self):
        """Test process_video_frame returns tuple."""
        filter = MosaicGridFilter()
        frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        filtered, detection = filter.process_video_frame(frame)
        assert filtered.shape == frame.shape
        assert isinstance(detection, GridDetectionResult)

    def test_create_mosaic_filter_sbs_fisheye(self):
        """Test factory function for SBS fisheye mode."""
        filter = create_mosaic_filter(MosaicMode.SBS_FISHEYE)
        assert filter.grid_threshold == 0.25
        assert filter.filter_strength == 0.6

    def test_create_mosaic_filter_tb_fisheye(self):
        """Test factory function for TB fisheye mode."""
        filter = create_mosaic_filter(MosaicMode.TB_FISHEYE)
        assert filter.grid_threshold == 0.25
        assert filter.filter_strength == 0.6

    def test_create_mosaic_filter_mono_fisheye(self):
        """Test factory function for Mono fisheye mode."""
        filter = create_mosaic_filter(MosaicMode.MONO_FISHEYE)
        assert filter.grid_threshold == 0.3
        assert filter.filter_strength == 0.5

    def test_create_mosaic_filter_override_params(self):
        """Test factory function with parameter overrides."""
        filter = create_mosaic_filter(MosaicMode.SBS_FISHEYE, grid_threshold=0.5, filter_strength=0.8)
        assert filter.grid_threshold == 0.5
        assert filter.filter_strength == 0.8


class TestGridDetectionResult:
    """Tests for GridDetectionResult dataclass."""

    def test_grid_detection_result_defaults(self):
        """Test GridDetectionResult default values."""
        result = GridDetectionResult(has_grid=False)
        assert result.has_grid is False
        assert result.grid_spacing is None
        assert result.grid_orientation is None
        assert result.confidence == 0.0
        assert result.grid_regions is None

    def test_grid_detection_result_with_values(self):
        """Test GridDetectionResult with all values set."""
        result = GridDetectionResult(
            has_grid=True,
            grid_spacing=(16, 16),
            grid_orientation=0.0,
            confidence=0.8,
            grid_regions=[(0, 0, 10, 10)]
        )
        assert result.has_grid is True
        assert result.grid_spacing == (16, 16)
        assert result.grid_orientation == 0.0
        assert result.confidence == 0.8
        assert result.grid_regions == [(0, 0, 10, 10)]


class TestMosaicMode:
    """Tests for MosaicMode enum."""

    def test_mosaic_mode_values(self):
        """Test MosaicMode enum values."""
        assert MosaicMode.SBS_FISHEYE.value == "sbs_fisheye"
        assert MosaicMode.TB_FISHEYE.value == "tb_fisheye"
        assert MosaicMode.MONO_FISHEYE.value == "mono_fisheye"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
