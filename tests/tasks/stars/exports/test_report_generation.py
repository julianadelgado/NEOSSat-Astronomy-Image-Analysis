from pathlib import Path
from unittest.mock import MagicMock, patch

from tasks.stars.constants import REPORTS_STARS_IMAGE_PATH, REPORTS_STARS_MAP_PATH
from tasks.stars.exports.report_generation import generate_report


@patch("tasks.stars.exports.report_generation.ReportService")
def test_generate_report_basic(mock_service, tmp_path: Path):
    output_dir = tmp_path

    img1 = output_dir / REPORTS_STARS_IMAGE_PATH
    img2 = output_dir / REPORTS_STARS_MAP_PATH

    img1.parent.mkdir(parents=True, exist_ok=True)
    img1.touch()
    img2.touch()

    instance = MagicMock()
    mock_service.return_value = instance

    generate_report(output_dir, {"stars_detected": 3})

    assert instance.generate.called


@patch("tasks.stars.exports.report_generation.ReportService")
def test_generate_report_no_images(mock_service, tmp_path: Path):
    output_dir = tmp_path

    instance = MagicMock()
    mock_service.return_value = instance

    generate_report(output_dir, {"stars_detected": 0})

    assert instance.generate.called


@patch("tasks.stars.exports.report_generation.ReportService")
def test_generate_report_missing_results_key(mock_service, tmp_path: Path):
    output_dir = tmp_path

    instance = MagicMock()
    mock_service.return_value = instance

    generate_report(output_dir, {})

    assert instance.generate.called
