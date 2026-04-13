from pathlib import Path

import astropy.units as units
import matplotlib
import numpy as np
from astropy.wcs import WCS

from cli.config import load_config
from processing.core.processor import IProcessor
from services.report_service import ReportData, ReportSection, ReportService
from tasks.stars.exports.heatmap_exporter import render_heatmaps
from services.simbad.simbad_service import query_simbad_skycoord
from tasks.stars.detection.region_identifier import get_image_region

from tasks.stars.detection.source_identifier import detect_sources, match_candidates
from tasks.stars.exports.csv_exporter import export_results
from tasks.stars.exports.image_exporter import render_region_image
from tasks.stars.exports.map_exporter import render_region_map, render_region_catalog_map
from tasks.stars.exports.magnitude_data_exporter import render_magnitude_plot

from tasks.stars.constants import FLUX_THRESHOLD

matplotlib.use("Agg")

SIGMA = 3.0
DAO_FINDER_FWHM = 3.0
DAO_FINDER_THRESHOLD = 5.0

SATURATION_PERCENTILE = 99.9
CLUSTER_EPS = 3.0
MATCH_THRESHOLD_DEFAULT = 15.0 * units.arcsec
MATCH_THRESHOLD_BRIGHT = 45.0 * units.arcsec

CANDIDATE_NOT_FOUND_STRING = "not_found"

FIGSIZE = (10, 10)
VMIN_PERCENTILE = 5
VMAX_PERCENTILE = 99

FILTERS = ["B", "V", "R", "J", "H", "K"]

TYPE_SYMBOLS = {
    "star": {"marker": "+", "color": "red"},
    "planet": {"marker": "*", "color": "green"},
    "star cluster": {"marker": "D", "color": "magenta"},
    "galaxies": {"marker": "o", "color": "blue"},
    "galaxies set": {"marker": "s", "color": "orange"},
    "spectral source": {"marker": "^", "color": "cyan"},
    "nebula": {"marker": "v", "color": "yellow"},
    "cloud": {"marker": "p", "color": "brown"},
    "Default": {"marker": "x", "color": "purple"},
}

config = load_config(None)

OUTPUT_DIR = Path(config.results_dir)
REPORTS_DIR = Path(config.reports_dir)


class StarDetection(IProcessor):

    def name(self) -> str:
        return "star_detection"

    def run(self, image: np.ndarray, header, output_dir: Path, **kwargs) -> dict:

        wcs = WCS(header)

        center, radius = get_image_region(image, wcs)

        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "simbad_request_results.csv"

        region_catalog = query_simbad_skycoord(center, radius, output_csv_path=csv_path)

        render_region_catalog_map(
            image=image, wcs=wcs, region_catalog=region_catalog, output_dir=output_dir
        )

        detected_candidates = detect_sources(image, wcs, header)

        detected_candidates = [
            src for src in detected_candidates if src["flux"] >= FLUX_THRESHOLD
        ]

        print(f"Filtered {len(detected_candidates) - len(detected_candidates)} faint candidates based on flux")

        if len(detected_candidates) == 0:
            return {"stars_detected": 0}

        matched_candidates = match_candidates(detected_candidates, region_catalog)

        export_results(matched_candidates, output_dir)

        render_region_image(image, wcs, matched_candidates, output_dir)
        render_region_map(image, matched_candidates, output_dir)
        render_heatmaps(image, matched_candidates, output_dir)
        render_magnitude_plot(matched_candidates, output_dir)

        self._generate_report(output_dir, {"stars_detected": len(matched_candidates)})

        return {"stars_detected": len(matched_candidates)}

    def _generate_report(self, output_dir: Path, results: dict):

        report_service = ReportService(reports_dir=REPORTS_DIR)

        star_images = [
            p
            for p in [
                output_dir / "detected_stars_img.png",
                output_dir / "detected_stars_map.png",
                output_dir / "region_catalog_map.png",
                output_dir / "candidates_heatmap.png",
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