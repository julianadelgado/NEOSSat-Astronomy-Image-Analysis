from pathlib import Path

from matplotlib import pyplot as plt

from tasks.stars.constants import FILTERS, REPORTS_MAGNITUDE_PLOT_PATH
from tasks.stars.detected_star import DetectedStar


def render_magnitude_plot(matched_candidates: list[DetectedStar], output_dir: Path):

    matched_objects = [
        c
        for c in matched_candidates
        if c.is_matched() and c.object_id is not None and c.magnitude_obs is not None
    ]

    if not matched_objects:
        print("No matched stars to plot magnitudes.")
        return

    matched_objects.sort(key=lambda c: c.magnitude_obs)

    object_ids = [c.object_id for c in matched_objects]
    mag_obs = [c.magnitude_obs for c in matched_objects]

    sim_mags = {
        f: [getattr(c, f"mag_{f.lower()}") for c in matched_objects] for f in FILTERS
    }

    fig, ax = plt.subplots(figsize=(8, max(6, len(object_ids) * 0.4)))
    ax.set_facecolor("white")
    ax.grid(True, linestyle="--", alpha=0.5)

    y = range(len(object_ids))

    ax.scatter(mag_obs, y, color="black", marker="o", label="Observed")

    colors = ["blue", "green", "red", "orange", "purple", "brown"]

    for f, col in zip(FILTERS, colors):
        ax.scatter(sim_mags[f], y, color=col, marker="s", label=f"SIMBAD {f}")

    ax.invert_xaxis()

    ax.set_yticks(list(y))
    ax.set_yticklabels(object_ids, fontsize=8)

    ax.set_ylabel("Object ID")
    ax.set_xlabel("Magnitude")
    ax.set_title("Magnitudes (Observed vs SIMBAD)")

    ax.legend(loc="best", fontsize=8)

    valid_mags = [m for m in mag_obs if m is not None]
    if valid_mags:
        ax.axvline(min(valid_mags), color="gray", linestyle="--")
        ax.axvline(max(valid_mags), color="gray", linestyle=":")

    output_dir.mkdir(parents=True, exist_ok=True)
    plot_path = output_dir / REPORTS_MAGNITUDE_PLOT_PATH

    plt.tight_layout()
    plt.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Magnitude plot saved to {plot_path}")
