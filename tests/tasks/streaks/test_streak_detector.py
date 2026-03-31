from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tasks.streaks.dl_streak_detector import DLStreakDetector


def test_streak_detector_neos_sci_2024239174545_cord():
    data_dir = Path(__file__).parent / "test_data"
    source_file = data_dir / "NEOS_SCI_2024239174545_cord.fits"
    if not source_file.exists():
        pytest.skip(f"Test file {source_file} not found")

    # Initialize the detector
    detector = DLStreakDetector(data_dir=str(data_dir), clean_results=True)

    detector.satellite_db = MagicMock()
    detector.satellite_db.correlate_streak_with_satellite.return_value = None

    # Run inference
    result = detector.run()

    # Ensure successful execution
    assert "error" not in result
    assert "streaks" in result

    streaks = result["streaks"]
    assert len(streaks) == 1

    file_result = streaks[0]
    assert file_result["file"] == "NEOS_SCI_2024239174545_cord"

    detections = file_result.get("detections", [])

    # We expect exactly 2 unique streak detections now that the duplication bug is fixed
    assert len(detections) == 2

    # Identify detections by confidence
    det_39 = next((d for d in detections if abs(d["confidence"] - 0.39) < 0.05), None)
    det_76 = next((d for d in detections if abs(d["confidence"] - 0.76) < 0.05), None)

    assert det_39 is not None, "Detection with confidence ~0.39 not found"
    assert det_76 is not None, "Detection with confidence ~0.76 not found"

    # RA and Dec value checks for the first detection (~0.39)
    # 121.3436348519709 deg RA
    assert abs(det_39["world_coords"]["ra_deg"] - 121.343) < 0.01
    # -41.11415296800481 deg Dec
    assert abs(det_39["world_coords"]["dec_deg"] - (-41.114)) < 0.01
    assert "satellite_correlation" not in det_39

    # RA and Dec value checks for the second detection (~0.76)
    # 121.42054243893524 deg RA
    assert abs(det_76["world_coords"]["ra_deg"] - 121.420) < 0.01
    # -41.026383690323684 deg Dec
    assert abs(det_76["world_coords"]["dec_deg"] - (-41.026)) < 0.01
