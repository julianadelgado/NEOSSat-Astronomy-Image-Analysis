from pathlib import Path

import matplotlib
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from tasks.stars.constants import (
    CANDIDATE_NOT_FOUND_STRING,
    FIGSIZE,
    REPORTS_REGION_MAP_PATH,
    REPORTS_STARS_MAP_PATH,
    TYPE_SYMBOLS,
)
from tasks.stars.detected_star import DetectedStar
from tasks.stars.map_groups import map_to_group

matplotlib.use("Agg")


def _build_legend(ax, seen_groups):
    legend_elements = [
        Line2D(
            [0],
            [0],
            marker=info["marker"],
            color=info["color"],
            label=group,
            markersize=8,
            fillstyle="none",
            linewidth=0,
        )
        for group, info in TYPE_SYMBOLS.items()
        if group in seen_groups
    ]

    ax.legend(
        handles=legend_elements,
        facecolor="black",
        labelcolor="white",
        loc="upper right",
    )


def render_region_map(image, matched_candidates: list[DetectedStar], output_dir: Path):

    output_dir.mkdir(parents=True, exist_ok=True)
    map_path = output_dir / REPORTS_STARS_MAP_PATH

    fig, ax = plt.subplots(figsize=FIGSIZE)
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")
    ax.axis("off")
    ax.set_xlim(0, image.shape[1])
    ax.set_ylim(0, image.shape[0])

    for candidate in matched_candidates:
        object_id = candidate.object_id or CANDIDATE_NOT_FOUND_STRING

        if object_id != CANDIDATE_NOT_FOUND_STRING:
            ax.plot(candidate.x, candidate.y, marker=".", color="white", markersize=6)

        otype = candidate.otype or "Default"
        group = map_to_group(otype)
        symbol_info = TYPE_SYMBOLS.get(group, TYPE_SYMBOLS["Default"])

        ax.plot(
            candidate.x,
            candidate.y,
            marker=symbol_info["marker"],
            color=symbol_info["color"],
            markersize=8,
            label=object_id if object_id != CANDIDATE_NOT_FOUND_STRING else None,
            fillstyle="none",
            linewidth=1.5,
        )

    seen_groups = {map_to_group(c.otype or "Default") for c in matched_candidates}
    _build_legend(ax, seen_groups)

    plt.savefig(map_path, dpi=300, bbox_inches="tight", pad_inches=0)
    plt.close(fig)

    print(f"Region map with detected stars saved to {map_path}")


def render_region_catalog_map(image, wcs, region_catalog, output_dir: Path):

    if len(region_catalog) == 0:
        print("Region catalog is empty, nothing to render.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    map_path = output_dir / REPORTS_REGION_MAP_PATH

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

    seen_groups = {
        map_to_group(getattr(obj, "otype", "Default")) for obj in region_catalog
    }
    _build_legend(ax, seen_groups)

    plt.savefig(map_path, dpi=300, bbox_inches="tight", pad_inches=0)
    plt.close(fig)

    print(f"Region catalog map saved to {map_path}")
