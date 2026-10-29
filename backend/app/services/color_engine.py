"""Color metadata extraction and preservation engine."""
import subprocess
import json
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ColorMetadata:
    """Video color metadata extracted from source."""
    pix_fmt: Optional[str] = None
    color_range: Optional[str] = None
    color_space: Optional[str] = None
    color_transfer: Optional[str] = None
    color_primaries: Optional[str] = None
    chroma_location: Optional[str] = None


class ColorMetadataExtractor:
    """Extract and preserve color metadata from video files using ffprobe."""

    def __init__(self, ffprobe_path: str = "ffprobe"):
        self.ffprobe_path = ffprobe_path

    def extract(self, video_path: str) -> ColorMetadata:
        """Extract color metadata from video file."""
        cmd = [
            self.ffprobe_path,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=pix_fmt,color_range,color_space,color_transfer,color_primaries,chroma_location",
            "-of", "json",
            video_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return ColorMetadata()

            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            if not streams:
                return ColorMetadata()

            stream = streams[0]
            return ColorMetadata(
                pix_fmt=stream.get("pix_fmt"),
                color_range=stream.get("color_range"),
                color_space=stream.get("color_space"),
                color_transfer=stream.get("color_transfer"),
                color_primaries=stream.get("color_primaries"),
                chroma_location=stream.get("chroma_location"),
            )
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError):
            return ColorMetadata()

    def build_ffmpeg_color_args(self, metadata: ColorMetadata) -> list[str]:
        """Build ffmpeg arguments to preserve color metadata."""
        args = []

        if metadata.color_primaries and metadata.color_primaries != "unknown":
            args.extend(["-color_primaries", metadata.color_primaries])

        if metadata.color_transfer and metadata.color_transfer != "unknown":
            args.extend(["-color_trc", metadata.color_transfer])

        if metadata.color_space and metadata.color_space != "unknown":
            args.extend(["-colorspace", metadata.color_space])

        if metadata.color_range and metadata.color_range != "unknown":
            args.extend(["-color_range", metadata.color_range])

        if metadata.chroma_location and metadata.chroma_location != "unknown":
            args.extend(["-chroma_location", metadata.chroma_location])

        return args


class ColorCorrectionEngine:
    """Color space correction to prevent green tint from BT.709 misassignment."""

    # Known problematic conversions that cause green tint
    PROBLEMATIC_DEFAULTS = {
        "color_space": "bt709",
        "color_transfer": "bt709",
        "color_primaries": "bt709",
        "chroma_location": "left",  # Should be 'center' for most sources
    }

    def __init__(self, extractor: Optional[ColorMetadataExtractor] = None):
        self.extractor = extractor or ColorMetadataExtractor()

    def analyze_source(self, video_path: str) -> ColorMetadata:
        """Analyze source video color metadata."""
        return self.extractor.extract(video_path)

    def should_apply_correction(self, source: ColorMetadata, target: ColorMetadata) -> bool:
        """Determine if color correction is needed."""
        # If source has unknown/unset color metadata but target has bt709 defaults,
        # this is likely the green tint bug
        if (source.color_space in (None, "unknown", "") and
            target.color_space == "bt709"):
            return True

        # Chroma location mismatch (center -> left)
        if (source.chroma_location in ("center", None, "") and
            target.chroma_location == "left"):
            return True

        return False

    def get_corrected_metadata(self, source: ColorMetadata) -> ColorMetadata:
        """Get corrected metadata that preserves source intent."""
        # If source has explicit metadata, use it
        # If source is unknown, don't force bt709 - let player infer
        corrected = ColorMetadata()

        # Preserve source pix_fmt
        corrected.pix_fmt = source.pix_fmt

        # Only set explicit color metadata if source had it
        if source.color_range and source.color_range != "unknown":
            corrected.color_range = source.color_range
        # Else leave unset - don't force tv range

        if source.color_space and source.color_space != "unknown":
            corrected.color_space = source.color_space
        # Else leave unset - don't force bt709

        if source.color_transfer and source.color_transfer != "unknown":
            corrected.color_transfer = source.color_transfer

        if source.color_primaries and source.color_primaries != "unknown":
            corrected.color_primaries = source.color_primaries

        # Only set chroma_location if source had explicit value
        if source.chroma_location and source.chroma_location != "unknown":
            corrected.chroma_location = source.chroma_location
        # Else leave unset - don't force center

        return corrected

    def build_export_args(self, source: ColorMetadata) -> list[str]:
        """Build ffmpeg export arguments with corrected color metadata."""
        corrected = self.get_corrected_metadata(source)
        return self.extractor.build_ffmpeg_color_args(corrected)


def detect_green_tint_risk(source_metadata: ColorMetadata) -> bool:
    """Detect if a video is at risk for green tint artifact."""
    # Videos with unknown color metadata that get forced to bt709 are at risk
    return (
        source_metadata.color_space in (None, "unknown", "") and
        source_metadata.color_primaries in (None, "unknown", "")
    )