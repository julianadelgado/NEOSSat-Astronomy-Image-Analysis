import csv
from pathlib import Path

import astropy.units as units
import matplotlib
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from photutils.detection import DAOStarFinder
from sklearn.cluster import DBSCAN

from cli.config import load_config
from processing.core.processor import IProcessor
from services.report_service import ReportData, ReportSection, ReportService
from tasks.stars.heatmap import generate_heatmap
from tasks.stars.map_groups import map_to_group
from tasks.stars.queries import query_simbad_skycoord

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

        center, radius = self._get_image_region(image, wcs)

        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "simbad_request_results.csv"

        region_catalog = query_simbad_skycoord(center, radius, output_csv_path=csv_path)

        self._render_region_catalog_map(
            image=image, wcs=wcs, region_catalog=region_catalog, output_dir=output_dir
        )

        detected_candidates = self._detect_sources(image, wcs, header)

        FLUX_THRESHOLD = 1.05
        filtered_candidates = [
            src for src in detected_candidates
            if src["flux"] >= FLUX_THRESHOLD
        ]

        print(f"Filtered {len(detected_candidates) - len(filtered_candidates)} faint candidates based on flux")
        detected_candidates = filtered_candidates

        if len(detected_candidates) == 0:
            return {"stars_detected": 0}

        matched_candidates = self._match_candidates(detected_candidates, region_catalog)

        self._export_results(matched_candidates, output_dir)

        self._render_region_image(
            image, wcs, detected_candidates, matched_candidates, output_dir
        )

        self._render_region_map(
            image, wcs, detected_candidates, matched_candidates, output_dir
        )

        self._render_heatmaps(
            image, wcs, detected_candidates, matched_candidates, output_dir
        )

        self._render_magnitude_plot(matched_candidates, output_dir)

        self._generate_report(output_dir, {"stars_detected": len(matched_candidates)})

        return {"stars_detected": len(matched_candidates)}

    """===> Private Functions <==="""

    def _get_image_region(self, image: np.ndarray, wcs: WCS):
        """Calculate the center and radius of the image region"""

        height, width = image.shape
        x_corners = [0, width, 0, width]
        y_corners = [0, 0, height, height]

        corner_coords = wcs.pixel_to_world(x_corners, y_corners)

        center = SkyCoord(ra=np.mean(corner_coords.ra), dec=np.mean(corner_coords.dec))

        center_coord_str = f"RA={center.ra.deg:.4f} deg, Dec={center.dec.deg:.4f} deg"

        print(f"Image region center: {center_coord_str}")

        separations = center.separation(corner_coords)
        radius = separations.max()

        print(f"Image region radius: {radius.arcmin:.2f} arcmin")

        return center, radius

    def _detect_sources(self, image: np.ndarray, wcs, header):
        """Extract light sources from source image, compute flux and approximate magnitude."""

        mean, median, std = sigma_clipped_stats(image, sigma=SIGMA)
        daofind = DAOStarFinder(fwhm=DAO_FINDER_FWHM, threshold=DAO_FINDER_THRESHOLD * std)

        sources = daofind(image - median)
        detected_candidates = []

        if sources is None or len(sources) == 0:
            print("DAOStarFinder - No sources found.")
            return []

        exptime = header.get("EXPOSURE", header.get("AEXPTIME", 1.0))
        gain = float(header.get("GAIN", 1.0))
        zp = 25.0 # This value needs to be tuned or update. AB - 07/04/2026

        x_coord = sources["xcentroid"]
        y_coord = sources["ycentroid"]
        flux = sources["flux"]

        coords_array = np.column_stack((x_coord, y_coord))
        clustering = DBSCAN(eps=CLUSTER_EPS, min_samples=1).fit(coords_array)

        for cluster_label in np.unique(clustering.labels_):
            cluster_indices = np.where(clustering.labels_ == cluster_label)[0]
            x_mean = np.mean(x_coord[cluster_indices])
            y_mean = np.mean(y_coord[cluster_indices])
            flux_sum = np.sum(flux[cluster_indices])
            world_coord = wcs.pixel_to_world(x_mean, y_mean)

            try:
                magnitude = -2.5 * np.log10(flux_sum / exptime * gain) + zp
            except:
                magnitude = None

            detected_candidates.append({
                "x": float(x_mean),
                "y": float(y_mean),
                "coord": world_coord,
                "flux": float(flux_sum),
                "magnitude": float(magnitude) if magnitude is not None else None,
                "saturated": False
            })

        saturation_threshold = np.percentile(image, SATURATION_PERCENTILE)
        saturated_mask = image >= saturation_threshold

        if np.any(saturated_mask):
            from scipy.ndimage import label, center_of_mass

            labeled, n_objects = label(saturated_mask)
            for i in range(1, n_objects + 1):
                mask_i = labeled == i
                y_c, x_c = center_of_mass(mask_i)
                world_coord = wcs.pixel_to_world(x_c, y_c)
                flux_sum = np.sum(image[mask_i])

                try:
                    magnitude = -2.5 * np.log10(flux_sum / exptime * gain) + zp
                except:
                    magnitude = None

                detected_candidates.append({
                    "x": float(x_c),
                    "y": float(y_c),
                    "coord": world_coord,
                    "flux": float(flux_sum),
                    "magnitude": float(magnitude) if magnitude is not None else None,
                    "saturated": True
                })

        print(f"Stars detected: {len(detected_candidates)}")
        return detected_candidates

    def _match_candidates(self, detected_candidates, region_catalog):
        if len(detected_candidates) == 0:
            return []

        if len(region_catalog) == 0:
            return [{
                **src,
                "object_id": CANDIDATE_NOT_FOUND_STRING,
                "otype": "Default",
                "deviation_arcsec": None,
                "sim_b": None,
                "sim_v": None,
                "sim_r": None
            } for src in detected_candidates]

        detected_coords = SkyCoord([src["coord"] for src in detected_candidates])
        catalog_coords = SkyCoord([obj.coord for obj in region_catalog])
        idx, sep2d, _ = detected_coords.match_to_catalog_sky(catalog_coords)

        matched_candidates = []
        magnitudes_obs = []

        for i, src in enumerate(detected_candidates):

            sep_threshold = MATCH_THRESHOLD_BRIGHT if src["flux"] > np.percentile([c["flux"] for c in detected_candidates], 99) else MATCH_THRESHOLD_DEFAULT
            separation = sep2d[i]

            if separation < sep_threshold:
                matched_obj = region_catalog[idx[i]]
                matched_candidates.append({
                    **src,
                    "object_id": matched_obj.object_id,
                    "otype": getattr(matched_obj, "otype", "Default"),
                    "deviation_arcsec": separation.arcsec,
                    "sim_b": getattr(matched_obj, "mag_b_val", None),
                    "sim_v": getattr(matched_obj, "mag_v_val", None),
                    "sim_r": getattr(matched_obj, "mag_r_val", None),
                })
            else:
                matched_candidates.append({
                    **src,
                    "object_id": CANDIDATE_NOT_FOUND_STRING,
                    "otype": "Default",
                    "deviation_arcsec": separation.arcsec,
                    "sim_b": None,
                    "sim_v": None,
                    "sim_r": None
                })

            if src.get("magnitude") is not None:
                magnitudes_obs.append(src["magnitude"])

        if magnitudes_obs:
            print(f"Observed magnitudes: min={min(magnitudes_obs):.2f}, max={max(magnitudes_obs):.2f}")

        sim_mags = [obj.mag_v_val for obj in region_catalog if obj.mag_v_val is not None]
        if sim_mags:
            print(f"SIMBAD catalog magnitudes (V): min={min(sim_mags):.2f}, max={max(sim_mags):.2f}")
            print(f"Number of expected stars in frame: {len(sim_mags)}")

        matched_count = sum(1 for c in matched_candidates if c["object_id"] != CANDIDATE_NOT_FOUND_STRING)
        print(f"Matched {matched_count} candidates with catalog objects.")

        return matched_candidates

    def _export_results(self, matched_candidates, output_dir: Path):
        """Export matched candidates to a CSV file"""

        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "star_detection_results.csv"

        with open(csv_path, mode="w", newline="") as file:

            writer = csv.writer(file)

            writer.writerow(
                [
                    "id", "x_pixel", "y_pixel", "ra_deg", "dec_deg",
                    "flux", "magnitude_obs",
                    "object_id", "otype", "deviation_arcsec",
                    "mag_b_simbad", "mag_v_simbad", "mag_r_simbad"
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
                        candidate.get("sim_b"),
                        candidate.get("sim_v"),
                        candidate.get("sim_r")
                    ]
                )

        print(f"Star detection results exported to {csv_path}")

    def _render_region_image(
        self, image, wcs, detected_candidates, matched_candidates, output_dir: Path
    ):
        """Generate an image of the region with detected stars highlighted"""

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

            if object_id != CANDIDATE_NOT_FOUND_STRING:
                ax.plot(
                    x_star,
                    y_star,
                    marker="o",
                    markersize=8,
                    markeredgecolor="cyan",
                    markerfacecolor="none",
                    label=object_id,
                    linewidth=1.5,
                )
            else:
                ax.plot(
                    x_star,
                    y_star,
                    marker="o",
                    markersize=8,
                    markeredgecolor="red",
                    markerfacecolor="none",
                    linewidth=1.5,
                )

        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)

        print(f"Region image with detected stars saved to {output_path}")

    def _render_region_map(
        self, image, wcs, detected_candidates, matched_candidates, output_dir: Path
    ):
        """Generate an image of the region with stars highlighted with otypes"""

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

    def _render_heatmaps(
        self, image, wcs, detected_candidates, matched_candidates, output_dir: Path
    ):
        """Generate heatmaps for detected candidates."""

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
        """Generate a map showing all objects in the SIMBAD region catalog."""

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
        """Visualize magnitudes (observed + SIMBAD) for matched stars with object_id on X-axis."""

        matched_objects = [c for c in matched_candidates if c["object_id"] != CANDIDATE_NOT_FOUND_STRING]

        if not matched_objects:
            print("No matched stars to plot magnitudes.")
            return

        object_ids = [c["object_id"] for c in matched_objects]
        mag_obs = [c.get("magnitude") for c in matched_objects]
        mag_b_simbad = [c.get("sim_b") for c in matched_objects]
        mag_v_simbad = [c.get("sim_v") for c in matched_objects]
        mag_r_simbad = [c.get("sim_r") for c in matched_objects]

        fig, ax = plt.subplots(figsize=(max(12, len(object_ids) * 0.5), 6))
        ax.set_facecolor("white")
        ax.grid(True, linestyle="--", alpha=0.5)

        x = range(len(object_ids))

        ax.scatter(x, mag_obs, color="black", marker="o", label="Observed")

        ax.scatter(x, mag_b_simbad, color="blue", marker="s", label="SIMBAD B")
        ax.scatter(x, mag_v_simbad, color="green", marker="s", label="SIMBAD V")
        ax.scatter(x, mag_r_simbad, color="red", marker="s", label="SIMBAD R")

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
            ax.axhline(min_mag, color="gray", linestyle="--", alpha=0.7, label=f"Min observed ({min_mag:.2f})")
            ax.axhline(max_mag, color="gray", linestyle=":", alpha=0.7, label=f"Max observed ({max_mag:.2f})")
            ax.text(0, min_mag, f'MIN ({min_mag:.2f})', color='gray', fontsize=10, verticalalignment='bottom')
            ax.text(0, max_mag, f'MAX ({max_mag:.2f})', color='gray', fontsize=10, verticalalignment='top')

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
