from pathlib import Path

import matplotlib
import numpy as np
from astropy.wcs import WCS

from processing.core.processor import IProcessor
from services.simbad.simbad_service import query_simbad_skycoord
from tasks.stars.constants import FLUX_THRESHOLD
from tasks.stars.detection.region_identifier import get_image_region
from tasks.stars.detection.source_identifier import detect_sources, match_candidates
from tasks.stars.exports.csv_exporter import export_results
from tasks.stars.exports.heatmap_exporter import render_heatmaps
from tasks.stars.exports.image_exporter import render_region_image
from tasks.stars.exports.magnitude_data_exporter import render_magnitude_plot
from tasks.stars.exports.map_exporter import (
    render_region_catalog_map,
    render_region_map,
)
from tasks.stars.exports.report_generation import generate_report

matplotlib.use("Agg")


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

        initial_count = len(detected_candidates)

        detected_candidates = [
            src for src in detected_candidates if src.flux >= FLUX_THRESHOLD
        ]

        filtered_count = initial_count - len(detected_candidates)

        print(f"Filtered {filtered_count} faint candidates based on flux")

        if len(detected_candidates) == 0:
            return {"stars_detected": 0}

        matched_candidates = match_candidates(detected_candidates, region_catalog)

        export_results(matched_candidates, output_dir)

        render_region_image(image, wcs, matched_candidates, output_dir)
        render_region_map(image, matched_candidates, output_dir)
        render_heatmaps(image, matched_candidates, output_dir)
        render_magnitude_plot(matched_candidates, output_dir)

        generate_report(output_dir, {"stars_detected": len(matched_candidates)})

        return {"stars_detected": len(matched_candidates)}
