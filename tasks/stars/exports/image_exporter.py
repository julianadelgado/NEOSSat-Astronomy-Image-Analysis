from pathlib import Path

import matplotlib
import matplotlib.patheffects as path_effects
import numpy as np

matplotlib.use("Agg")

from matplotlib import pyplot as plt
from tasks.stars.constants import (
    FIGSIZE,
    CANDIDATE_NOT_FOUND_STRING,
    VMAX_PERCENTILE,
    VMIN_PERCENTILE,
    REPORTS_STARS_IMAGE_PATH,
)

from tasks.stars.detected_star import DetectedStar


def render_region_image(image, wcs, matched_candidates: list[DetectedStar], output_dir: Path):

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / REPORTS_STARS_IMAGE_PATH

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
        object_id = star.object_id or CANDIDATE_NOT_FOUND_STRING

        color = "cyan" if object_id != CANDIDATE_NOT_FOUND_STRING else "red"

        ax.plot(
            star.x,
            star.y,
            marker="o",
            markersize=8,
            markeredgecolor=color,
            markerfacecolor="none",
            linewidth=1.5,
        )

        if object_id != CANDIDATE_NOT_FOUND_STRING:
            ax.text(
                star.x + 2,
                star.y + 2,
                object_id,
                color=color,
                fontsize=8,
                ha="left",
                va="bottom",
                path_effects=[
                    path_effects.withStroke(linewidth=2, foreground="black")
                ],
            )

    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Region image with detected stars saved to {output_path}")
