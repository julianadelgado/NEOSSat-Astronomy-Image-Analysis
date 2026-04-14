from pathlib import Path

import matplotlib
import matplotlib.patheffects as path_effects
import numpy as np
from matplotlib import pyplot as plt

from tasks.stars.constants import (
    FIGSIZE,
    REPORTS_STARS_IMAGE_PATH,
    VMAX_PERCENTILE,
    VMIN_PERCENTILE,
)

matplotlib.use("Agg")


def render_catalog_overlay(
    image,
    wcs,
    detected_candidates,
    region_catalog,
    output_dir: Path,
):
    """
    Debug overlay showing detected star candidates (cyan circles) and SIMBAD catalog objects (red crosses) on the image background.
     - Detected candidates: cyan circles
     - Catalog objects: red crosses
     - Background: original image
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "catalog_overlay_debug.png"

    fig = plt.figure(figsize=FIGSIZE)
    ax = plt.subplot(projection=wcs)

    ax.imshow(
        image,
        origin="lower",
        cmap="gray",
        vmin=np.percentile(image, VMIN_PERCENTILE),
        vmax=np.percentile(image, VMAX_PERCENTILE),
    )

    for star in detected_candidates:
        ax.plot(
            star.x,
            star.y,
            marker="o",
            markersize=6,
            markeredgecolor="cyan",
            markerfacecolor="none",
            linewidth=1.2,
        )

    # ------------------------
    # SIMBAD catalog
    # coord -> pixel via WCS
    # ------------------------
    for obj in region_catalog:
        try:
            x, y = wcs.world_to_pixel(obj.coord)
        except Exception:
            continue

        ax.plot(
            x,
            y,
            marker="+",
            markersize=10,
            markeredgecolor="red",
            markerfacecolor="none",
            linewidth=1.5,
        )

    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"[DEBUG] Catalog overlay saved to {output_path}")
