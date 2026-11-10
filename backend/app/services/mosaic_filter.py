"""Mosaic grid artifact detection and filtering for VR180 video restoration."""
import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, List


class MosaicMode(str, Enum):
    """VR180 mosaic layout modes."""
    SBS_FISHEYE = "sbs_fisheye"    # Side-by-side fisheye
    TB_FISHEYE = "tb_fisheye"      # Top-bottom fisheye
    MONO_FISHEYE = "mono_fisheye"  # Single fisheye


@dataclass
class GridDetectionResult:
    """Result of grid artifact detection."""
    has_grid: bool
    grid_spacing: Optional[Tuple[int, int]] = None
    grid_orientation: Optional[float] = None
    confidence: float = 0.0
    grid_regions: Optional[List[Tuple[int, int, int, int]]] = None


class MosaicGridFilter:
    """
    Detect and suppress grid pattern artifacts in VR180 mosaic removal.
    
    Grid artifacts appear as regular patterns from the mosaic tiling process
    in VR180 cameras. This filter detects the grid and applies spatial filtering
    to suppress it while preserving detail in non-mosaic areas.
    """
    
    def __init__(
        self,
        grid_threshold: float = 0.3,
        filter_strength: float = 0.5,
        min_grid_size: int = 8,
        max_grid_size: int = 64,
    ):
        self.grid_threshold = grid_threshold
        self.filter_strength = filter_strength
        self.min_grid_size = min_grid_size
        self.max_grid_size = max_grid_size
    
    def detect_grid(self, frame: np.ndarray) -> GridDetectionResult:
        """
        Detect grid pattern in frame using frequency domain analysis.
        
        Args:
            frame: Input frame (BGR or grayscale)
            
        Returns:
            GridDetectionResult with detection details
        """
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        h, w = gray.shape[:2]
        
        # Apply window function to reduce spectral leakage
        window = np.outer(np.hanning(h), np.hanning(w))
        windowed = gray.astype(np.float32) * window
        
        # Compute 2D FFT
        fft = np.fft.fft2(windowed)
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.log1p(np.abs(fft_shift))
        
        # Find peaks in frequency domain (excluding DC component)
        center_y, center_x = h // 2, w // 2
        
        # Search for regular grid peaks
        peak_coords = self._find_grid_peaks(magnitude, center_y, center_x)
        
        if len(peak_coords) < 4:
            return GridDetectionResult(has_grid=False, confidence=0.0)
        
        # Analyze peak pattern to determine grid spacing and orientation
        spacing, orientation = self._analyze_grid_pattern(peak_coords, center_y, center_x)
        
        if spacing is None:
            return GridDetectionResult(has_grid=False, confidence=0.0)
        
        grid_w, grid_h = spacing
        
        # Validate grid size
        if not (self.min_grid_size <= grid_w <= self.max_grid_size and
                self.min_grid_size <= grid_h <= self.max_grid_size):
            return GridDetectionResult(has_grid=False, confidence=0.0)
        
        # Calculate confidence based on peak regularity
        confidence = self._calculate_confidence(peak_coords, spacing, center_y, center_x)
        
        if confidence < self.grid_threshold:
            return GridDetectionResult(has_grid=False, confidence=confidence)
        
        # Find grid regions in spatial domain
        grid_regions = self._find_grid_regions(gray, grid_w, grid_h, orientation)
        
        return GridDetectionResult(
            has_grid=True,
            grid_spacing=(grid_w, grid_h),
            grid_orientation=orientation,
            confidence=confidence,
            grid_regions=grid_regions
        )
    
    def _find_grid_peaks(
        self,
        magnitude: np.ndarray,
        center_y: int,
        center_x: int
    ) -> List[Tuple[int, int]]:
        """Find candidate grid peaks in frequency domain."""
        peaks = []
        
        # Use adaptive threshold based on magnitude statistics
        mean_mag = np.mean(magnitude)
        std_mag = np.std(magnitude)
        threshold = mean_mag + 2.5 * std_mag
        
        # Search in annular region around center (exclude DC and very high frequencies)
        min_radius = max(center_y, center_x) // 20
        max_radius = max(center_y, center_x) // 3
        
        y_coords, x_coords = np.where(magnitude > threshold)
        
        for y, x in zip(y_coords, x_coords):
            dy, dx = y - center_y, x - center_x
            radius = np.sqrt(dy*dy + dx*dx)
            
            if min_radius <= radius <= max_radius:
                # Check if local maximum
                if self._is_local_max(magnitude, y, x):
                    peaks.append((y, x))
        
        return peaks
    
    def _is_local_max(self, arr: np.ndarray, y: int, x: int, window: int = 3) -> bool:
        """Check if point is local maximum in window."""
        h, w = arr.shape
        y1, y2 = max(0, y - window), min(h, y + window + 1)
        x1, x2 = max(0, x - window), min(w, x + window + 1)
        local = arr[y1:y2, x1:x2]
        return arr[y, x] == np.max(local)
    
    def _analyze_grid_pattern(
        self,
        peaks: List[Tuple[int, int]],
        center_y: int,
        center_x: int
    ) -> Tuple[Optional[Tuple[int, int]], Optional[float]]:
        """Analyze peak pattern to extract grid spacing and orientation."""
        if len(peaks) < 4:
            return None, None
        
        # Convert to vectors from center
        vectors = [(y - center_y, x - center_x) for y, x in peaks]
        
        # Cluster vectors by angle to find dominant orientations
        angles = [np.arctan2(vy, vx) for vy, vx in vectors]
        
        # Find two dominant perpendicular orientations (grid axes)
        # Use histogram of angles
        hist, bins = np.histogram(angles, bins=36, range=(-np.pi, np.pi))
        
        # Find peaks in histogram
        peak_bins = np.where(hist > np.max(hist) * 0.3)[0]
        
        if len(peak_bins) < 2:
            return None, None
        
        # Get dominant orientations
        dominant_angles = [(bins[i] + bins[i+1]) / 2 for i in peak_bins[:4]]
        
        # Find perpendicular pairs
        best_spacing = None
        best_orientation = None
        best_score = 0
        
        for i, a1 in enumerate(dominant_angles):
            for a2 in dominant_angles[i+1:]:
                # Check if roughly perpendicular
                diff = abs(abs(a1 - a2) - np.pi/2)
                if diff < np.pi/6:  # Within 30 degrees of perpendicular
                    # Estimate spacing from vector positions
                    # For a grid with spacing S, frequency peaks are at k * N / S
                    # So fundamental frequency radius = N / S, thus S = N / radius
                    mags1 = [np.sqrt(vy*vy + vx*vx) for vy, vx in vectors 
                            if abs(np.arctan2(vy, vx) - a1) < np.pi/12]
                    mags2 = [np.sqrt(vy*vy + vx*vx) for vy, vx in vectors
                            if abs(np.arctan2(vy, vx) - a2) < np.pi/12]
                    
                    if mags1 and mags2:
                        # Determine which axis is which based on angle
                        # a1 closer to 0 or pi -> horizontal, pi/2 -> vertical
                        is_a1_horizontal = abs(a1) < np.pi/4 or abs(abs(a1) - np.pi) < np.pi/4
                        
                        # Use the MINIMUM radius for fundamental frequency (not median)
                        # Median picks up harmonics; min gives fundamental spacing
                        min_r1 = np.min(mags1)
                        min_r2 = np.min(mags2)
                        
                        if is_a1_horizontal:
                            spacing_x = int(center_x * 2 / min_r1) if min_r1 > 0 else None
                            spacing_y = int(center_y * 2 / min_r2) if min_r2 > 0 else None
                        else:
                            spacing_y = int(center_y * 2 / min_r1) if min_r1 > 0 else None
                            spacing_x = int(center_x * 2 / min_r2) if min_r2 > 0 else None
                        
                        if spacing_x and spacing_y:
                            score = len(mags1) + len(mags2)
                            if score > best_score:
                                best_score = score
                                best_spacing = (spacing_x, spacing_y)
                                best_orientation = a1
        
        return best_spacing, best_orientation
    
    def _calculate_confidence(
        self,
        peaks: List[Tuple[int, int]],
        spacing: Tuple[int, int],
        center_y: int,
        center_x: int
    ) -> float:
        """Calculate confidence score for grid detection."""
        grid_w, grid_h = spacing
        expected_peaks = 0
        matched_peaks = 0
        
        # Expected peak positions for a regular grid
        for ky in range(-3, 4):
            for kx in range(-3, 4):
                if ky == 0 and kx == 0:
                    continue
                expected_peaks += 1
                py = center_y + ky * (center_y // grid_h)
                px = center_x + kx * (center_x // grid_w)
                
                # Check if there's a peak nearby
                for py_peak, px_peak in peaks:
                    if abs(py_peak - py) < 3 and abs(px_peak - px) < 3:
                        matched_peaks += 1
                        break
        
        return matched_peaks / max(expected_peaks, 1)
    
    def _find_grid_regions(
        self,
        gray: np.ndarray,
        grid_w: int,
        grid_h: int,
        orientation: float
    ) -> List[Tuple[int, int, int, int]]:
        """Find grid line regions in spatial domain."""
        h, w = gray.shape[:2]
        regions = []
        
        # Grid lines (horizontal and vertical based on orientation)
        cos_o = np.cos(orientation)
        sin_o = np.sin(orientation)
        
        # For simplicity, assume axis-aligned grid (most common case)
        # Vertical grid lines - thin regions (2 pixels wide)
        for x in range(0, w, grid_w):
            regions.append((0, max(0, x-1), h, min(w, x+1)))
        
        # Horizontal grid lines - thin regions (2 pixels tall)
        for y in range(0, h, grid_h):
            regions.append((max(0, y-1), 0, min(h, y+1), w))
        
        return regions

    def filter_frame(self, frame: np.ndarray, detection: Optional[GridDetectionResult] = None) -> np.ndarray:
        """
        Apply grid artifact suppression to frame.
        
        Args:
            frame: Input frame (BGR)
            detection: Optional pre-computed detection result
            
        Returns:
            Filtered frame with grid artifacts suppressed
        """
        if detection is None:
            detection = self.detect_grid(frame)
        
        if not detection.has_grid or detection.grid_regions is None:
            return frame
        
        result = frame.copy().astype(np.float32)
        h, w = frame.shape[:2]
        
        # Create mask for grid lines only (thin lines, not full spans)
        mask = np.zeros((h, w), dtype=np.float32)
        if detection.grid_spacing:
            grid_w, grid_h = detection.grid_spacing
            # Vertical grid lines (2 pixels wide)
            for x in range(0, w, grid_w):
                x1, x2 = max(0, x-1), min(w, x+1)
                mask[:, x1:x2] = 1.0
            # Horizontal grid lines (2 pixels tall)
            for y in range(0, h, grid_h):
                y1, y2 = max(0, y-1), min(h, y+1)
                mask[y1:y2, :] = 1.0
        
        # Apply bilateral filter to grid regions to smooth artifacts
        # while preserving edges in non-grid areas
        filtered = cv2.bilateralFilter(frame, d=9, sigmaColor=75, sigmaSpace=75)
        
        # Blend filtered grid regions with original
        for c in range(3):
            result[:, :, c] = frame[:, :, c] * (1 - mask * self.filter_strength) + \
                              filtered[:, :, c] * (mask * self.filter_strength)
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def process_video_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, GridDetectionResult]:
        """
        Process a single video frame: detect and filter grid artifacts.
        
        Returns:
            Tuple of (filtered_frame, detection_result)
        """
        detection = self.detect_grid(frame)
        filtered = self.filter_frame(frame, detection)
        return filtered, detection


def create_mosaic_filter(
    mode: MosaicMode,
    **kwargs
) -> MosaicGridFilter:
    """Factory function to create filter with mode-specific defaults."""
    mode_configs = {
        MosaicMode.SBS_FISHEYE: {"grid_threshold": 0.25, "filter_strength": 0.6},
        MosaicMode.TB_FISHEYE: {"grid_threshold": 0.25, "filter_strength": 0.6},
        MosaicMode.MONO_FISHEYE: {"grid_threshold": 0.3, "filter_strength": 0.5},
    }
    config = mode_configs.get(mode, {})
    config.update(kwargs)
    return MosaicGridFilter(**config)
