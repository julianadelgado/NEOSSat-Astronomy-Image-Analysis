import csv
from pathlib import Path

import astropy.units as units
import matplotlib
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from photutils.detection import DAOStarFinder

from preprocessing.core.preprocessor import IPreprocessor
from tasks.stars.heatmap import generate_heatmap
from tasks.stars.map_groups import map_to_group
from tasks.stars.queries import query_simbad_skycoord

matplotlib.use("Agg")

from matplotlib import pyplot as plt  # noqa: E402

# flake8 doesn't like the non-top-level import but we need
# to set the backend before importing pyplot - AB 16/03/2026

SIGMA = 3.0
DAO_FINDER_FWHM = 3.0
DAO_FINDER_THRESHOLD = 5.0
MATCH_THRESHOLD = 30.0 * units.arcsec

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


class StarDetection(IPreprocessor):

    def name(self) -> str:
        return "star_detection"

    def run(self, image: np.ndarray, header, output_dir: Path) -> dict:

        wcs = WCS(header)

        center, radius = self._get_image_region(image, wcs)

        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "simbad_request_results.csv"

        region_catalog = query_simbad_skycoord(center, radius, output_csv_path=csv_path)

        self._render_region_catalog_map(
            image=image, wcs=wcs, region_catalog=region_catalog, output_dir=output_dir
        )

        detected_candidates = self._detect_sources(image, header, wcs)

        if len(detected_candidates) == 0:
            return {"stars_detected": 0}

        matched_candidates = self._match_candidates(detected_candidates, region_catalog, header)

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

    def _detect_sources(self, image: np.ndarray, header, wcs: WCS):
        """Run source detection on the image using DAOStarFinder"""

        print("Running source detection...")

        try:
            gain = float(header.get("GAIN", 1.0))
        except (ValueError, TypeError):
            gain = 1.0

        try:
            read_noise = float(header.get("RDNOISE", 8.0))
        except (ValueError, TypeError):
            read_noise = 8.0

        effective_std = max(read_noise / gain, np.std(image))

        print(f"Using GAIN={gain}, READ_NOISE={read_noise}, EFFECTIVE_STD={effective_std} (IMAGE_STD={np.std(image)}).")

        mean, median, std = sigma_clipped_stats(image, sigma=SIGMA, maxiters=5)

        daofind = DAOStarFinder(
            fwhm=DAO_FINDER_FWHM, threshold=DAO_FINDER_THRESHOLD * effective_std
        )

        sources = daofind(image - median)

        print(f"Found {len(sources)} potential star candidates.")

        if sources is None or len(sources) == 0:
            print("No sources detected.")
            return []

        x_coord = sources["xcentroid"]
        y_coord = sources["ycentroid"]
        flux = sources["flux"]

        world_coords = wcs.pixel_to_world(x_coord, y_coord)

        min_flux = 5 * effective_std
        detected_candidates = [
            {
                "x": float(x_coord[i]),
                "y": float(y_coord[i]),
                "coord": world_coords[i],
                "flux": float(flux[i]),
            }
            for i in range(len(sources))
            if flux[i] > min_flux
        ]

        print(
            f"Detected {len(detected_candidates)} star candidates after DAOStarFinder."
        )

        return detected_candidates

    def _match_candidates(self, detected_candidates, region_catalog, header):
        matched = []

        filter_band = header.get("FILTER", None)

        for candidate in detected_candidates:
            best_match = None
            min_sep = MATCH_THRESHOLD

            for entry in region_catalog:
                sep = candidate["coord"].separation(entry["coord"])

                flux_match = 1.0
                if filter_band and "magnitude_" + filter_band.lower() in entry:
                    flux_diff = abs(candidate["flux"] - entry["magnitude_" + filter_band.lower()])
                    flux_match = 1.0 / (1.0 + flux_diff)

                weighted_sep = sep / flux_match

                if weighted_sep < min_sep:
                    min_sep = weighted_sep
                    best_match = entry

            if best_match:
                matched.append({**candidate, "matched_entry": best_match})
            else:
                matched.append({**candidate, "matched_entry": CANDIDATE_NOT_FOUND_STRING})

        return matched

    def _export_results(self, matched_candidates, output_dir: Path):
        """Export matched candidates to a CSV file"""

        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "star_detection_results.csv"

        with open(csv_path, mode="w", newline="") as file:

            writer = csv.writer(file)

            writer.writerow(
                [
                    "id",
                    "x_pixel",
                    "y_pixel",
                    "ra_deg",
                    "dec_deg",
                    "flux",
                    "object_id",
                    "deviation_arcsec",
                ]
            )

            for i, candidate in enumerate(matched_candidates):

                ra_deg = candidate["coord"].ra.deg
                dec_deg = candidate["coord"].dec.deg
                deviation = candidate.get("deviation_arcsec")
                object_id = candidate.get("object_id", CANDIDATE_NOT_FOUND_STRING)

                writer.writerow(
                    [
                        i,
                        candidate["x"],
                        candidate["y"],
                        ra_deg,
                        dec_deg,
                        candidate["flux"],
                        object_id,
                        (
                            deviation
                            if deviation is not None
                            else CANDIDATE_NOT_FOUND_STRING
                        ),
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
