from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")

from matplotlib import pyplot as plt  # noqa: E402
from tasks.stars.constants import FIGSIZE, CANDIDATE_NOT_FOUND_STRING, VMAX_PERCENTILE, VMIN_PERCENTILE


def render_region_image(
    image, wcs, matched_candidates, output_dir: Path
):

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
            markeredgecolor=(
                "cyan" if object_id != CANDIDATE_NOT_FOUND_STRING else "red"
            ),
            markerfacecolor="none",
            linewidth=1.5,
        )

    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Region image with detected stars saved to {output_path}")
