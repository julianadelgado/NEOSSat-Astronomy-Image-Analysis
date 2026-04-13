import csv
from pathlib import Path

import astropy.units as units
import matplotlib
import numpy as np
from astropy.wcs import WCS

from cli.config import load_config
from processing.core.processor import IProcessor
from services.report_service import ReportData, ReportSection, ReportService
from tasks.stars.heatmap import generate_heatmap
from tasks.stars.map_groups import map_to_group
from services.simbad.simbad_service import query_simbad_skycoord
from tasks.stars.detection.region_identifier import get_image_region

from tasks.stars.detection.source_identifier import detect_sources, match_candidates

matplotlib.use("Agg")

from matplotlib import pyplot as plt  # noqa: E402

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

        self._render_region_catalog_map(
            image=image, wcs=wcs, region_catalog=region_catalog, output_dir=output_dir
        )

        detected_candidates = detect_sources(image, wcs, header)

        FLUX_THRESHOLD = 1.05
        detected_candidates = [
            src for src in detected_candidates if src["flux"] >= FLUX_THRESHOLD
        ]

        print(f"Filtered {len(detected_candidates) - len(detected_candidates)} faint candidates based on flux")

        if len(detected_candidates) == 0:
            return {"stars_detected": 0}

        matched_candidates = match_candidates(detected_candidates, region_catalog)

        self._export_results(matched_candidates, output_dir)

        self._render_region_image(image, wcs, detected_candidates, matched_candidates, output_dir)
        self._render_region_map(image, wcs, detected_candidates, matched_candidates, output_dir)
        self._render_heatmaps(image, wcs, detected_candidates, matched_candidates, output_dir)
        self._render_magnitude_plot(matched_candidates, output_dir)

        self._generate_report(output_dir, {"stars_detected": len(matched_candidates)})

        return {"stars_detected": len(matched_candidates)}

    def _export_results(self, matched_candidates, output_dir: Path):

        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "star_detection_results.csv"

        with open(csv_path, mode="w", newline="") as file:

            writer = csv.writer(file)

            writer.writerow(
                [
                    "id", "x_pixel", "y_pixel", "ra_deg", "dec_deg",
                    "flux", "magnitude_obs",
                    "object_id", "otype", "deviation_arcsec",
                    *[f"mag_{f.lower()}_simbad" for f in FILTERS],
                ]
            )

            for i, candidate in enumerate(matched_candidates):
                writer.writerow(
                    [
                        i,
                        candidate["x"],
                        candidate["y"],
                        candidate["coord"].ra.deg,
                        candidate["coord"].dec.deg,
                        candidate["flux"],
                        candidate.get("magnitude"),
                        candidate.get("object_id", CANDIDATE_NOT_FOUND_STRING),
                        candidate.get("otype", "Default"),
                        candidate.get("deviation_arcsec", CANDIDATE_NOT_FOUND_STRING),
                        *[candidate.get(f"sim_{f.lower()}") for f in FILTERS],
                    ]
                )

        print(f"Star detection results exported to {csv_path}")

    def _render_region_image(self, image, wcs, detected_candidates, matched_candidates, output_dir: Path):

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "detected_stars_img.png"

        fig = plt.figure(figsize=FIGSIZE)
        ax = plt.subplot(projection=wcs)

        ax.imshow(
            image,
            origin="lower",
            cmap="gray",
            vmin=np.percentile(image, VMIN_PERCENTILE),
            vmax=np.percentile(image, VMAX_PERCENTILE),
        )

        for star in matched_candidates:
            x_star = star["x"]
            y_star = star["y"]
            object_id = star.get("object_id", CANDIDATE_NOT_FOUND_STRING)

            ax.plot(
                x_star,
                y_star,
                marker="o",
                markersize=8,
                markeredgecolor="cyan" if object_id != CANDIDATE_NOT_FOUND_STRING else "red",
                markerfacecolor="none",
                linewidth=1.5,
            )

        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)

        print(f"Region image with detected stars saved to {output_path}")

    def _render_region_map(self, image, wcs, detected_candidates, matched_candidates, output_dir: Path):

        output_dir.mkdir(parents=True, exist_ok=True)
        map_path = output_dir / "detected_stars_map.png"

        fig, ax = plt.subplots(figsize=FIGSIZE)
        fig.patch.set_facecolor("black")
        ax.set_facecolor("black")
        ax.axis("off")
        ax.set_xlim(0, image.shape[1])
        ax.set_ylim(0, image.shape[0])

        for candidate in matched_candidates:
            x_star = candidate["x"]
            y_star = candidate["y"]

            object_id = candidate.get("object_id", CANDIDATE_NOT_FOUND_STRING)

            if object_id != CANDIDATE_NOT_FOUND_STRING:
                ax.plot(x_star, y_star, marker=".", color="white", markersize=6)

            otype = candidate.get("otype", "Default")
            group = map_to_group(otype)
            symbol_info = TYPE_SYMBOLS.get(group, TYPE_SYMBOLS["Default"])

            ax.plot(
                x_star,
                y_star,
                marker=symbol_info["marker"],
                color=symbol_info["color"],
                markersize=8,
                label=object_id if object_id != CANDIDATE_NOT_FOUND_STRING else None,
                fillstyle="none",
                linewidth=1.5,
            )

        plt.savefig(map_path, dpi=300, bbox_inches="tight", pad_inches=0)
        plt.close(fig)

        print(f"Region map with detected stars saved to {map_path}")

    def _render_heatmaps(self, image, wcs, detected_candidates, matched_candidates, output_dir: Path):

        output_dir.mkdir(parents=True, exist_ok=True)

        if len(matched_candidates) == 0:
            print("No candidates to generate heatmaps.")
            return

        x_coords = [src["x"] for src in matched_candidates]
        y_coords = [src["y"] for src in matched_candidates]
        flux_values = [src["flux"] for src in matched_candidates]

        heatmap_path = output_dir / "candidates_heatmap.png"
        generate_heatmap(
            x_coords,
            y_coords,
            flux_values,
            image.shape,
            heatmap_path,
            bins=50,
            title="Detected Stars Heatmap",
        )

        print(f"Heatmap of detected stars saved to {heatmap_path}")

    def _render_region_catalog_map(self, image, wcs, region_catalog, output_dir: Path):

        if len(region_catalog) == 0:
            print("Region catalog is empty, nothing to render.")
            return

        output_dir.mkdir(parents=True, exist_ok=True)
        map_path = output_dir / "region_catalog_map.png"

        fig, ax = plt.subplots(figsize=FIGSIZE)
        fig.patch.set_facecolor("black")
        ax.set_facecolor("black")
        ax.axis("off")
        ax.set_xlim(0, image.shape[1])
        ax.set_ylim(0, image.shape[0])

        for obj in region_catalog:
            x_pix, y_pix = wcs.world_to_pixel(obj.coord)
            otype = getattr(obj, "otype", "Default")
            group = map_to_group(otype)
            symbol_info = TYPE_SYMBOLS.get(group, TYPE_SYMBOLS["Default"])

            ax.plot(
                x_pix,
                y_pix,
                marker=symbol_info["marker"],
                color=symbol_info["color"],
                markersize=8,
                label=obj.object_id,
                fillstyle="none",
                linewidth=1.5,
            )

        plt.savefig(map_path, dpi=300, bbox_inches="tight", pad_inches=0)
        plt.close(fig)

        print(f"Region catalog map saved to {map_path}")

    def _render_magnitude_plot(self, matched_candidates, output_dir: Path):

        matched_objects = [c for c in matched_candidates if c["object_id"] != CANDIDATE_NOT_FOUND_STRING]

        if not matched_objects:
            print("No matched stars to plot magnitudes.")
            return

        object_ids = [c["object_id"] for c in matched_objects]
        mag_obs = [c.get("magnitude") for c in matched_objects]

        sim_mags = {
            f: [c.get(f"sim_{f.lower()}") for c in matched_objects]
            for f in FILTERS
        }

        fig, ax = plt.subplots(figsize=(max(12, len(object_ids) * 0.5), 6))
        ax.set_facecolor("white")
        ax.grid(True, linestyle="--", alpha=0.5)

        x = range(len(object_ids))

        ax.scatter(x, mag_obs, color="black", marker="o", label="Observed")

        colors = ["blue", "green", "red", "orange", "purple", "brown"]
        for f, col in zip(FILTERS, colors):
            ax.scatter(x, sim_mags[f], color=col, marker="s", label=f"SIMBAD {f}")

        ax.invert_yaxis()
        ax.set_xticks(x)
        ax.set_xticklabels(object_ids, rotation=90, fontsize=8)
        ax.set_xlabel("Object ID")
        ax.set_ylabel("Magnitude")
        ax.set_title("Magnitudes")
        ax.legend(loc="upper right", fontsize=8)

        valid_mags = [m for m in mag_obs if m is not None]
        if valid_mags:
            min_mag = min(valid_mags)
            max_mag = max(valid_mags)
            ax.axhline(min_mag, color="gray", linestyle="--")
            ax.axhline(max_mag, color="gray", linestyle=":")

        output_dir.mkdir(parents=True, exist_ok=True)
        plot_path = output_dir / "magnitudes_plot.png"
        plt.tight_layout()
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close(fig)

        print(f"Magnitude plot saved to {plot_path}")

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