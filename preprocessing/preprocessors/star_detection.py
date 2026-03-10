import csv
from pathlib import Path

import numpy as np
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from photutils.detection import DAOStarFinder

from preprocessing.core.preprocessor import IPreprocessor
from preprocessing.core.queries import query_simbad
import astropy.units as units
from preprocessing.analysis.heatmap import generate_heatmap
from matplotlib.patches import Circle

# simbad_acceptance_radius = 2 * units.arcmin
simbad_acceptance_radius = 45 * units.arcsec
show_acceptance_radius = True  # Debug only - AB 10/03/2026

# Code quite long, will be refactored before pull request, debug/tuning only for now
# AB 25/02/2026


class StarDetection(IPreprocessor):

    def name(self) -> str:
        return "star_detection"

    def run(self, image: np.ndarray, header, output_dir: Path) -> dict:
        wcs = WCS(header)

        mean, median, std = sigma_clipped_stats(image, sigma=3.0)
        daofind = DAOStarFinder(
            fwhm=3.0,
            threshold=5.0 * std,
        )
        sources = daofind(image - median)

        if sources is None:
            return {"stars_detected": 0}

        x = sources["xcentroid"]
        y = sources["ycentroid"]
        flux = sources["flux"]
        world = wcs.pixel_to_world(x, y)
        ra = world.ra.deg
        dec = world.dec.deg

        plot_data = []

        # Write CSV
        csv_path = output_dir / "detected_stars.csv"
        with open(csv_path, mode="w", newline="") as f:
            writer = csv.writer(f)
            header = [
                "id",
                "x_pixel",
                "y_pixel",
                "ra_deg",
                "dec_deg",
                "flux",
                "object_id",
                "deviation"
            ]
            writer.writerow(header)
            enum = enumerate(zip(x, y, ra, dec, flux))

            for star, (x_star, y_star, ra_star, dec_star, flux_star) in enum:

                full_coord_string = f"{ra_star} {dec_star}"

                print("[SIMBAD QUERY] ", full_coord_string)

                identified_obj = query_simbad(
                    full_coord_string,
                    simbad_acceptance_radius
                )

                if identified_obj is not None:
                    id_star = identified_obj.object_id
                    deviation_star = identified_obj.distance_arcsec
                else:
                    id_star = "not_found"
                    deviation_star = "not_found"

                writer.writerow([
                    star,
                    x_star,
                    y_star,
                    ra_star,
                    dec_star,
                    flux_star,
                    id_star,
                    deviation_star
                ])

                plot_data.append({
                    "x": x_star,
                    "y": y_star,
                    "flux": flux_star,
                    "id": id_star,
                    "deviation": deviation_star if deviation_star != "not_found" else None
                })

        # Annotated image
        # Imports placed here to avoid module-level side-effects
        # flagged by black, isort, and flake8
        # AB - 25/02/2026
        import matplotlib as _matplotlib

        _matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(10, 10))
        ax = plt.subplot(projection=wcs)
        ax.imshow(
            image,
            cmap="gray",
            origin="lower",
            vmin=float(np.percentile(image, 5)),
            vmax=float(np.percentile(image, 99)),
        )

        for star in plot_data:
            x_star = star["x"]
            y_star = star["y"]
            id_star = star["id"]

            if id_star != "not_found":

                ax.plot(
                    x_star,
                    y_star,
                    marker="o",
                    markersize=8,
                    color="cyan",
                    fillstyle="none",
                    linewidth=1.5
                )

                ax.text(
                    x_star + 5,
                    y_star + 5,
                    id_star,
                    color="cyan",
                    fontsize=6
                )

            else:
                ax.plot(
                    x_star,
                    y_star,
                    marker="o",
                    markersize=8,
                    color="red",
                    fillstyle="none",
                    linewidth=1.2
                )

            # Acceptance radius visualization, debug only - AB 10/03/2026
            if show_acceptance_radius:
                star_coord = wcs.pixel_to_world(x_star, y_star)
                radius_coord = star_coord.directional_offset_by(0*units.deg, simbad_acceptance_radius)
                x_radius, y_radius = wcs.world_to_pixel(radius_coord)
                radius_pix = np.sqrt((x_radius - x_star)**2 + (y_radius - y_star)**2)

                circle = Circle(
                    (x_star, y_star),
                    radius_pix,
                    edgecolor="yellow",
                    facecolor="none",
                    linewidth=1,
                    linestyle="--"
                )
                ax.add_patch(circle)

        img_path = output_dir / "detected_stars_img.png"
        plt.savefig(img_path, dpi=300, bbox_inches="tight")
        plt.close(fig)

        x_vals = []
        y_vals = []
        dev_vals = []

        for star in plot_data:
            if star["deviation"] is not None:
                x_vals.append(star["x"])
                y_vals.append(star["y"])
                dev_vals.append(star["deviation"])

        generate_heatmap(
            x_vals,
            y_vals,
            dev_vals,
            image.shape,
            output_dir / "heatmap_deviation.png",
            title="Deviation Heatmap"
        )

        x_vals = []
        y_vals = []
        values = []

        for star in plot_data:
            x_vals.append(star["x"])
            y_vals.append(star["y"])

            if star["id"] == "not_found":
                values.append(1)
            else:
                values.append(0)

        generate_heatmap(
            x_vals,
            y_vals,
            values,
            image.shape,
            output_dir / "heatmap_unidentified.png",
            title="Unidentified Sources Density"
        )

        x_vals = [s["x"] for s in plot_data]
        y_vals = [s["y"] for s in plot_data]

        generate_heatmap(
            x_vals,
            y_vals,
            np.ones(len(x_vals)),
            image.shape,
            output_dir / "heatmap_source_density.png",
            title="Detected Sources Density"
        )

        x_vals = [s["x"] for s in plot_data]
        y_vals = [s["y"] for s in plot_data]
        flux_vals = [s["flux"] for s in plot_data]

        generate_heatmap(
            x_vals,
            y_vals,
            flux_vals,
            image.shape,
            output_dir / "heatmap_flux.png",
            title="Flux Heatmap"
        )

        return {"stars_detected": len(x)}
