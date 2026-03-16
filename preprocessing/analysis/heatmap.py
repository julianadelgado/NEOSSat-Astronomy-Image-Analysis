import numpy as np
import matplotlib.pyplot as plt


def generate_heatmap(
    x_coords, y_coords, values, image_shape, output_path, bins=50, title="Heatmap"
):

    heatmap, xedges, yedges = np.histogram2d(
        x_coords, y_coords, bins=bins, weights=values
    )

    counts, _, _ = np.histogram2d(x_coords, y_coords, bins=bins)

    with np.errstate(divide="ignore", invalid="ignore"):
        heatmap = heatmap / counts
        heatmap[np.isnan(heatmap)] = 0

    plt.figure(figsize=(10, 8))

    plt.imshow(heatmap.T, origin="lower", cmap="inferno", interpolation="nearest")

    plt.colorbar(label="value")
    plt.title(title)
    plt.xlabel("X bins")
    plt.ylabel("Y bins")

    plt.savefig(output_path, dpi=300)
    plt.close()
