from pathlib import Path

from services.report_service import ReportData, ReportSection, ReportService
from tasks.stars.constants import (
    REPORTS_DIR,
    REPORTS_NAME_SEPARATOR,
    REPORTS_REGION_CATEGORY,
    REPORTS_STARS_CATEGORY,
    REPORTS_MAGNITUDE_CATEGORY,
    REPORTS_IMAGE_SUFFIX,
    REPORTS_MAP_SUFFIX,
    REPORTS_HEATMAP_SUFFIX,
)


def generate_report(output_dir: Path, results: dict):

    report_service = ReportService(reports_dir=REPORTS_DIR)

    star_images = [
        p
        for p in [
            output_dir / f"{REPORTS_STARS_CATEGORY}{REPORTS_NAME_SEPARATOR}{REPORTS_IMAGE_SUFFIX}",
            output_dir / f"{REPORTS_STARS_CATEGORY}{REPORTS_NAME_SEPARATOR}{REPORTS_MAP_SUFFIX}",
            output_dir / f"{REPORTS_REGION_CATEGORY}{REPORTS_NAME_SEPARATOR}{REPORTS_MAP_SUFFIX}",
            output_dir / f"{REPORTS_STARS_CATEGORY}{REPORTS_NAME_SEPARATOR}{REPORTS_HEATMAP_SUFFIX}",
        ]
        if p.exists()
    ]

    report_service.generate(
        ReportData(
            task_name="Star Detection",
            sections=[
                ReportSection(
                    title=f"Results for {output_dir.name}",
                    content=f"Stars detected: {results.get('stars_detected', 0)}",
                    images=star_images,
                )
            ],
        )
    )
