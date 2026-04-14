from pathlib import Path

from tasks.stars.constants import REPORTS_STARS_IMAGE_PATH, REPORTS_STARS_MAP_PATH
from tasks.stars.exports.report_generation import generate_report


def test_generate_report_basic(tmp_path: Path):
    output_dir = tmp_path

    img1 = output_dir / REPORTS_STARS_IMAGE_PATH
    img2 = output_dir / REPORTS_STARS_MAP_PATH

    img1.parent.mkdir(parents=True, exist_ok=True)
    img1.touch()
    img2.touch()

    section = generate_report(output_dir, {"stars_detected": 3})

    assert section.title == f"Results for {output_dir.name}"
    assert "Stars detected: 3" in section.content
    assert len(section.images) == 2


def test_generate_report_no_images(tmp_path: Path):
    output_dir = tmp_path

    section = generate_report(output_dir, {"stars_detected": 0})

    assert section.content == "Stars detected: 0"
    assert section.images == []


def test_generate_report_missing_results_key(tmp_path: Path):
    output_dir = tmp_path

    section = generate_report(output_dir, {})

    assert "Stars detected: 0" in section.content
