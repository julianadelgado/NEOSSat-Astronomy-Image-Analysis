import csv
from pathlib import Path

import numpy as np
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from photutils.detection import DAOStarFinder

from preprocessing.core.preprocessor import IPreprocessor
from preprocessing.core.queries import query_simbad


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
                identified_obj = query_simbad(full_coord_string, "2m")

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

        for xi, yi in zip(x, y):
            ax.plot(
                xi,
                yi,
                marker="o",
                markersize=5,
                color="red",
                fillstyle="none",
            )

        img_path = output_dir / "detected_stars_img.png"
        plt.savefig(img_path, dpi=300, bbox_inches="tight")
        plt.close(fig)

        return {"stars_detected": len(x)}
