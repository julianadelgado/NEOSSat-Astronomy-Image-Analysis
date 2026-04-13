from pathlib import Path

from matplotlib import pyplot as plt # noqa: E402

from tasks.stars.constants import CANDIDATE_NOT_FOUND_STRING, FILTERS


def render_magnitude_plot(matched_candidates, output_dir: Path):

    matched_objects = [
        c for c in matched_candidates if c["object_id"] != CANDIDATE_NOT_FOUND_STRING
    ]

    if not matched_objects:
        print("No matched stars to plot magnitudes.")
        return

    object_ids = [c["object_id"] for c in matched_objects]
    mag_obs = [c.get("magnitude") for c in matched_objects]

    sim_mags = {
        f: [c.get(f"sim_{f.lower()}") for c in matched_objects] for f in FILTERS
    }

    fig, ax = plt.subplots(figsize=(max(12, len(object_ids) * 0.5), 6))
    ax.set_facecolor("white")
    ax.grid(True, linestyle="--", alpha=0.5)

    x = range(len(object_ids))

    ax.scatter(x, mag_obs, color="black", marker="o", label="Observed")

    colors = ["blue", "green", "red", "orange", "purple", "brown"]
    for f, col in zip(FILTERS, colors):
        ax.scatter(x, sim_mags[f], color=col, marker="s", label=f"SIMBAD {f}")

    ax.invert_yaxis()
    ax.set_xticks(x)
    ax.set_xticklabels(object_ids, rotation=90, fontsize=8)
    ax.set_xlabel("Object ID")
    ax.set_ylabel("Magnitude")
    ax.set_title("Magnitudes")
    ax.legend(loc="upper right", fontsize=8)

    valid_mags = [m for m in mag_obs if m is not None]
    if valid_mags:
        min_mag = min(valid_mags)
        max_mag = max(valid_mags)
        ax.axhline(min_mag, color="gray", linestyle="--")
        ax.axhline(max_mag, color="gray", linestyle=":")

    output_dir.mkdir(parents=True, exist_ok=True)
    plot_path = output_dir / "magnitudes_plot.png"
    plt.tight_layout()
    plt.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Magnitude plot saved to {plot_path}")
