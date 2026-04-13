from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from tasks.stars.constants import REPORTS_STARS_HEATMAP_PATH
from tasks.stars.detected_star import DetectedStar


def render_heatmaps(image, matched_candidates: list[DetectedStar], output_dir: Path):

    output_dir.mkdir(parents=True, exist_ok=True)

    if len(matched_candidates) == 0:
        print("No candidates to generate heatmaps.")
        return

    x_coords = [src.x for src in matched_candidates]
    y_coords = [src.y for src in matched_candidates]
    flux_values = [src.flux for src in matched_candidates]

    heatmap_path = output_dir / REPORTS_STARS_HEATMAP_PATH

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


def generate_heatmap(
    x_coords,
    y_coords,
    values,
    image_shape,
    output_path,
    bins=50,
    title="Heatmap",
):

    heatmap, _, _ = np.histogram2d(
        x_coords, y_coords, bins=bins, weights=values
    )

    counts, _, _ = np.histogram2d(x_coords, y_coords, bins=bins)

    with np.errstate(divide="ignore", invalid="ignore"):
        heatmap = heatmap / counts
        heatmap[np.isnan(heatmap)] = 0

    plt.figure(figsize=(10, 8))

    plt.imshow(
        heatmap.T,
        origin="lower",
        cmap="inferno",
        interpolation="nearest",
    )

    plt.colorbar(label="value")
    plt.title(title)
    plt.xlabel("X bins")
    plt.ylabel("Y bins")

    plt.savefig(output_path, dpi=300)
    plt.close()
