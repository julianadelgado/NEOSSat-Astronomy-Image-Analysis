from pathlib import Path

import matplotlib
import numpy as np
from astropy.wcs import WCS

from processing.core.processor import IProcessor
from services.report_service import ReportSection
from services.simbad.simbad_service import query_simbad_skycoord
from tasks.stars.constants import FLUX_THRESHOLD
from tasks.stars.detection.astrometric_alignment import (
    align_detected_to_catalog_with_image,
)
from tasks.stars.detection.region_identifier import get_image_region
from tasks.stars.detection.source_identifier import detect_sources
from tasks.stars.detection.source_matching import match_candidates
from tasks.stars.exports.catalog_overlay_exporter import render_catalog_overlay
from tasks.stars.exports.csv_exporter import export_results
from tasks.stars.exports.heatmap_exporter import render_heatmaps
from tasks.stars.exports.image_exporter import render_region_image
from tasks.stars.exports.magnitude_data_exporter import render_magnitude_plot
from tasks.stars.exports.map_exporter import (
    render_region_catalog_map,
    render_region_map,
)
from tasks.stars.exports.report_generation import generate_report, generate_debug_report

matplotlib.use("Agg")

DEBUG = True


class StarDetection(IProcessor):

    def name(self) -> str:
        return "star_detection"

    def run(self, image: np.ndarray, header, output_dir: Path, **kwargs) -> dict:

        # Added comments to clarify each step of the process
        # AB - 14/04/2026

        # 1 - Image TRIM (disabled)
        # TRIM_X = 15
        # image = image[:, :-TRIM_X]

        wcs = WCS(header)

        # Image TRIM (disabled)
        # wcs.wcs.crpix[0] -= TRIM_X

        # ----------------------------------------------------------
        # 2. Sky region identification & SIMBAD query
        # ----------------------------------------------------------
        center, radius = get_image_region(image, wcs)

        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "simbad_request_results.csv"

        region_catalog = query_simbad_skycoord(center, radius, output_csv_path=csv_path)

        # ----------------------------------------------------------
        # 3. SIMBAD catalog map rendering
        # ----------------------------------------------------------
        render_region_catalog_map(
            image=image,
            wcs=wcs,
            region_catalog=region_catalog,
            output_dir=output_dir,
        )

        # ----------------------------------------------------------
        # 4. Source detection
        # ----------------------------------------------------------
        detected_candidates = detect_sources(image, wcs, header)

        initial_count = len(detected_candidates)

        detected_candidates = [
            src for src in detected_candidates if src.flux >= FLUX_THRESHOLD
        ]

        filtered_count = initial_count - len(detected_candidates)
        print(f"Filtered {filtered_count} faint candidates based on flux")

        if len(detected_candidates) == 0:
            return {"stars_detected": 0}

        # -------------------------------------------------------------------
        # 4.5 Astrometric alignment of detected candidates to SIMBAD catalog
        # -------------------------------------------------------------------

        if DEBUG:
            detected_candidates, image = align_detected_to_catalog_with_image(
                detected_candidates,
                region_catalog,
                wcs,
                image,
            )

        # ----------------------------------------------------------
        # 5. Matching
        # ----------------------------------------------------------
        matched_candidates = match_candidates(detected_candidates, region_catalog)

        # ----------------------------------------------------------
        # 6. Debug overlay - should be removed in production -
        # ----------------------------------------------------------
        render_catalog_overlay(
            image=image,
            wcs=wcs,
            detected_candidates=detected_candidates,
            region_catalog=region_catalog,
            output_dir=output_dir,
        )

        # ----------------------------------------------------------
        # 7. Exports
        # ----------------------------------------------------------
        export_results(matched_candidates, output_dir)

        render_region_image(image, wcs, matched_candidates, output_dir)
        render_region_map(image, matched_candidates, output_dir)
        render_heatmaps(image, matched_candidates, output_dir)
        render_magnitude_plot(matched_candidates, output_dir)

        if not DEBUG:
            self._build_report_section(
                output_dir,
                {"stars_detected": len(matched_candidates)},
            )
        else:
            generate_debug_report(
                output_dir,
                {"stars_detected": len(matched_candidates)},
            )

        return {"stars_detected": len(matched_candidates)}

    def _build_report_section(self, output_dir: Path, results: dict) -> ReportSection:
        return generate_report(
            output_dir,
            results,
        )
