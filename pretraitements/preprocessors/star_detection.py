import csv
from pathlib import Path

import numpy as np
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from photutils.detection import DAOStarFinder

from pretraitements.core.IPreprocessor import IPreprocessor


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
        world = wcs.pixel_to_world(x, y)
        ra = world.ra.deg
        dec = world.dec.deg

        # Écriture CSV
        csv_path = output_dir / "etoiles_detectees.csv"
        with open(csv_path, mode="w", newline="") as f:
            writer = csv.writer(f)
            header = ["id", "x_pixel", "y_pixel", "ra_deg", "dec_deg"]
            writer.writerow(header)
            enum = enumerate(zip(x, y, ra, dec))
            for i, (xi, yi, rai, deci) in enum:
                writer.writerow([i, xi, yi, rai, deci])

        # Image annotée
        # Imports déplacés ici pour gérer black, isort et flake8, à discuter
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
            vmin=np.percentile(image, 5),
            vmax=np.percentile(image, 99),
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

        img_path = output_dir / "image_etoiles_detectees.png"
        plt.savefig(img_path, dpi=300, bbox_inches="tight")
        plt.close(fig)

        return {"stars_detected": len(x)}
