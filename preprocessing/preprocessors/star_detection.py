import csv
from pathlib import Path

import numpy as np
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from photutils.detection import DAOStarFinder

from preprocessing.core.preprocessor import IPreprocessor


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
        ctypes = [wcs.wcs.ctype[i].upper() for i in range(wcs.naxis)]
        ra_idx = next((i for i, c in enumerate(ctypes) if "RA" in c), None)
        dec_idx = next((i for i, c in enumerate(ctypes) if "DEC" in c), None)
        if ra_idx is not None and dec_idx is not None:
            pixel_in = np.zeros((len(x), wcs.naxis))
            pixel_in[:, 0] = x
            pixel_in[:, 1] = y
            world_out = wcs.all_pix2world(pixel_in, 0)
            ra = world_out[:, ra_idx]
            dec = world_out[:, dec_idx]
        else:
            ra = np.full(len(x), np.nan)
            dec = np.full(len(x), np.nan)

        # Write CSV
        csv_path = output_dir / "detected_stars.csv"
        with open(csv_path, mode="w", newline="") as f:
            writer = csv.writer(f)
            header = ["id", "x_pixel", "y_pixel", "ra_deg", "dec_deg"]
            writer.writerow(header)
            enum = enumerate(zip(x, y, ra, dec))
            for i, (xi, yi, rai, deci) in enum:
                writer.writerow([i, xi, yi, rai, deci])

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

        img_path = output_dir / "detected_stars_img.png"
        plt.savefig(img_path, dpi=300, bbox_inches="tight")
        plt.close(fig)

        return {"stars_detected": len(x)}
