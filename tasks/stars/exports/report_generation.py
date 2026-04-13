from pathlib import Path

from services.report_service import ReportData, ReportSection, ReportService
from tasks.stars.constants import (
    REPORTS_DIR,
    REPORTS_MAGNITUDE_PLOT_PATH,
    REPORTS_REGION_MAP_PATH,
    REPORTS_STARS_HEATMAP_PATH,
    REPORTS_STARS_IMAGE_PATH,
    REPORTS_STARS_MAP_PATH,
)


def generate_report(output_dir: Path, results: dict):

    report_service = ReportService(reports_dir=REPORTS_DIR)

    star_images = [
        p
        for p in [
            output_dir / REPORTS_STARS_IMAGE_PATH,
            output_dir / REPORTS_STARS_MAP_PATH,
            output_dir / REPORTS_REGION_MAP_PATH,
            output_dir / REPORTS_STARS_HEATMAP_PATH,
            output_dir / REPORTS_MAGNITUDE_PLOT_PATH,
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
