import csv
from pathlib import Path

import astropy.units as units
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from photutils.detection import DAOStarFinder

from preprocessing.analysis.heatmap import generate_heatmap
from preprocessing.core.preprocessor import IPreprocessor
from preprocessing.core.queries import query_simbad_skycoord

import matplotlib
matplotlib.use("Agg")

from matplotlib import pyplot as plt  # noqa: E402
# flake8 doesn't like the non-top-level import but we need
# to set the backend before importing pyplot - AB 16/03/2026

SIGMA = 3.0
DAO_FINDER_FWHM = 3.0
DAO_FINDER_THRESHOLD = 5.0
MATCH_THRESHOLD = 5.0 * units.arcsec

CANDIDATE_NOT_FOUND_STRING = "not_found"

FIGSIZE = (10, 10)
VMIN_PERCENTILE = 5
VMAX_PERCENTILE = 99


class StarDetection(IPreprocessor):

    def name(self) -> str:
        return "star_detection"

    def run(self, image: np.ndarray, header, output_dir: Path) -> dict:

        wcs = WCS(header)

        center, radius = self._get_image_region(image, wcs)

        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "simbad_request_results.csv"

        region_catalog = query_simbad_skycoord(
            center,
            radius,
            output_csv_path=csv_path
        )

        detected_candidates = self._detect_sources(image, wcs)

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

        return {"stars_detected": len(matched_candidates)}

    """===> Private Functions <==="""

    def _get_image_region(self, image: np.ndarray, wcs: WCS):
        """Calculate the center and radius of the image region in celestial coordinates."""

        height, width = image.shape
        x_corners = [0, width, 0, width]
        y_corners = [0, 0, height, height]

        corner_coords = wcs.pixel_to_world(x_corners, y_corners)

        center = SkyCoord(
            ra=np.mean(corner_coords.ra),
            dec=np.mean(corner_coords.dec)
        )

        print(f"Image region center: RA={center.ra.deg:.4f} deg, Dec={center.dec.deg:.4f} deg")

        separations = center.separation(corner_coords)
        radius = separations.max()

        print(f"Image region radius: {radius.arcmin:.2f} arcmin")

        return center, radius

    def _detect_sources(self, image: np.ndarray, wcs: WCS):

        print("Running source detection...")

        mean, median, std = sigma_clipped_stats(image, sigma=SIGMA)

        daofind = DAOStarFinder(
            fwhm=DAO_FINDER_FWHM,
            threshold=DAO_FINDER_THRESHOLD * std
        )

        sources = daofind(image - median)

        print(f"Found {len(sources)} potential star candidates.")

        if sources is None or len(sources) == 0:
            return []

        x_coord = sources['xcentroid']
        y_coord = sources['ycentroid']
        flux = sources['flux']

        world_coords = wcs.pixel_to_world(x_coord, y_coord)

        detected_candidates = []

        for i in range(len(sources)):

            detected_candidates.append({
                "x": float(x_coord[i]),
                "y": float(y_coord[i]),
                "coord": world_coords[i],
                "flux": float(flux[i])
            })

        print(f"Detected {len(detected_candidates)} star candidates after DAOStarFinder.")

        return detected_candidates

    def _match_candidates(self, detected_candidates, region_catalog):

        print("Matching detected candidates with catalog objects...")

        if len(detected_candidates) == 0:
            return []

        if len(region_catalog) == 0:
            matched = []
            for src in detected_candidates:
                matched.append({
                    **src,
                    "object_id": CANDIDATE_NOT_FOUND_STRING,
                    "deviation_arcsec": None
                })
            return matched

        detected_coords = SkyCoord([src["coord"] for src in detected_candidates])
        catalog_coords = SkyCoord([obj.coord for obj in region_catalog])

        idx, sep2d, _ = detected_coords.match_to_catalog_sky(catalog_coords)

        matched_candidates = []

        for i, src in enumerate(detected_candidates):
            separation = sep2d[i]
            if separation < MATCH_THRESHOLD:
                matched_candidates.append({
                    **src,
                    "object_id": region_catalog[idx[i]].object_id,
                    "deviation_arcsec": separation.arcsec
                })
            else:
                matched_candidates.append({
                    **src,
                    "object_id": CANDIDATE_NOT_FOUND_STRING,
                    "deviation_arcsec": separation.arcsec
                })

        identified_candidates = [
            c
            for c in matched_candidates
            if c["object_id"] != CANDIDATE_NOT_FOUND_STRING
        ]

        matched_count = len(identified_candidates)

        print(f"Matched {matched_count} candidates with catalog objects.")

        return matched_candidates

    def _export_results(self, matched_candidates, output_dir: Path):

        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "star_detection_results.csv"

        with open(csv_path, mode='w', newline="") as file:

            writer = csv.writer(file)

            writer.writerow([
                "id",
                "x_pixel",
                "y_pixel",
                "ra_deg",
                "dec_deg",
                "flux",
                "object_id",
                "deviation_arcsec"
            ])

            for i, candidate in enumerate(matched_candidates):

                ra_deg = candidate["coord"].ra.deg
                dec_deg = candidate["coord"].dec.deg
                deviation = candidate.get("deviation_arcsec")
                object_id = candidate.get("object_id", CANDIDATE_NOT_FOUND_STRING)

                writer.writerow([
                    i,
                    candidate["x"],
                    candidate["y"],
                    ra_deg,
                    dec_deg,
                    candidate["flux"],
                    object_id,
                    deviation if deviation is not None else CANDIDATE_NOT_FOUND_STRING
                ])

        print(f"Star detection results exported to {csv_path}")

    def _render_region_image(self, image, wcs, detected_candidates, matched_candidates, output_dir: Path):

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "detected_stars_img.png"

        fig = plt.figure(figsize=FIGSIZE)
        ax = plt.subplot(projection=wcs)

        ax.imshow(
            image,
            origin='lower',
            cmap='gray',
            vmin=np.percentile(image, VMIN_PERCENTILE),
            vmax=np.percentile(image, VMAX_PERCENTILE)
        )

        for star in matched_candidates:
            x_star = star["x"]
            y_star = star["y"]
            object_id = star.get("object_id", CANDIDATE_NOT_FOUND_STRING)

            if object_id != CANDIDATE_NOT_FOUND_STRING:
                ax.plot(
                    x_star,
                    y_star,
                    marker='o',
                    markersize=8,
                    markeredgecolor='cyan',
                    markerfacecolor='none',
                    label=object_id,
                    linewidth=1.5
                )
            else:
                ax.plot(
                    x_star,
                    y_star,
                    marker='o',
                    markersize=8,
                    markeredgecolor='red',
                    markerfacecolor='none',
                    linewidth=1.5
                )

        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        print(f"Region image with detected stars saved to {output_path}")

    def _render_region_map(
            self,
            image,
            wcs,
            detected_candidates,
            matched_candidates,
            output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)
        map_path = output_dir / "detected_stars_map.png"

        fig, ax = plt.subplots(figsize=FIGSIZE)
        ax.set_facecolor('black')
        ax.set_xlim(0, image.shape[1])
        ax.set_ylim(0, image.shape[0])
        # ax.invert_yaxis()

        type_symbols = {
            "Star": {"marker": "+", "color": "red"},
            "Galaxy": {"marker": "o", "color": "blue"},
            "Planetary Nebula": {"marker": "*", "color": "green"},
            "Open Cluster": {"marker": "D", "color": "magenta"},
            "Globular Cluster": {"marker": "s", "color": "orange"},
            "Default": {"marker": "x", "color": "purple"}
        }

        for candidate in matched_candidates:
            x_star = candidate["x"]
            y_star = candidate["y"]

            object_id = candidate.get("object_id", CANDIDATE_NOT_FOUND_STRING)

            if object_id != CANDIDATE_NOT_FOUND_STRING:
                ax.plot(x_star, y_star, marker=".", color="white", markersize=6)

            otype = candidate.get("otype", "Default")

            symbol_info = type_symbols.get(otype, type_symbols["Default"])

            ax.plot(
                x_star,
                y_star,
                marker=symbol_info["marker"],
                color=symbol_info["color"],
                markersize=8,
                label=object_id if object_id != CANDIDATE_NOT_FOUND_STRING else None,
                fillstyle="none",
                linewidth=1.5
            )

        ax.set_xlabel("X Pixel")
        ax.set_ylabel("Y Pixel")
        ax.set_title("Detected Stars Map")
        plt.savefig(map_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        print(f"Region map with detected stars saved to {map_path}")

    def _render_heatmaps(self, image, wcs, detected_candidates, matched_candidates, output_dir: Path):
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
            title="Detected Stars Heatmap"
        )

        print(f"Heatmap of detected stars saved to {heatmap_path}")
