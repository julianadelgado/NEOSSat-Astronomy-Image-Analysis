from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt  # noqa: E402
from tasks.stars.map_groups import map_to_group

from tasks.stars.constants import FIGSIZE, CANDIDATE_NOT_FOUND_STRING, TYPE_SYMBOLS


def render_region_map(
    image, matched_candidates, output_dir: Path
):

    output_dir.mkdir(parents=True, exist_ok=True)
    map_path = output_dir / "detected_stars_map.png"

    fig, ax = plt.subplots(figsize=FIGSIZE)
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")
    ax.axis("off")
    ax.set_xlim(0, image.shape[1])
    ax.set_ylim(0, image.shape[0])

    for candidate in matched_candidates:
        x_star = candidate["x"]
        y_star = candidate["y"]

        object_id = candidate.get("object_id", CANDIDATE_NOT_FOUND_STRING)

        if object_id != CANDIDATE_NOT_FOUND_STRING:
            ax.plot(x_star, y_star, marker=".", color="white", markersize=6)

        otype = candidate.get("otype", "Default")
        group = map_to_group(otype)
        symbol_info = TYPE_SYMBOLS.get(group, TYPE_SYMBOLS["Default"])

        ax.plot(
            x_star,
            y_star,
            marker=symbol_info["marker"],
            color=symbol_info["color"],
            markersize=8,
            label=object_id if object_id != CANDIDATE_NOT_FOUND_STRING else None,
            fillstyle="none",
            linewidth=1.5,
        )

    plt.savefig(map_path, dpi=300, bbox_inches="tight", pad_inches=0)
    plt.close(fig)

    print(f"Region map with detected stars saved to {map_path}")


def render_region_catalog_map(image, wcs, region_catalog, output_dir: Path):

    if len(region_catalog) == 0:
        print("Region catalog is empty, nothing to render.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    map_path = output_dir / "region_catalog_map.png"

    fig, ax = plt.subplots(figsize=FIGSIZE)
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")
    ax.axis("off")
    ax.set_xlim(0, image.shape[1])
    ax.set_ylim(0, image.shape[0])

    for obj in region_catalog:
        x_pix, y_pix = wcs.world_to_pixel(obj.coord)
        otype = getattr(obj, "otype", "Default")
        group = map_to_group(otype)
        symbol_info = TYPE_SYMBOLS.get(group, TYPE_SYMBOLS["Default"])

        ax.plot(
            x_pix,
            y_pix,
            marker=symbol_info["marker"],
            color=symbol_info["color"],
            markersize=8,
            label=obj.object_id,
            fillstyle="none",
            linewidth=1.5,
        )

    plt.savefig(map_path, dpi=300, bbox_inches="tight", pad_inches=0)
    plt.close(fig)

    print(f"Region catalog map saved to {map_path}")
