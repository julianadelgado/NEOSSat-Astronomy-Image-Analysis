import csv
from pathlib import Path
from tasks.stars.constants import FILTERS
from tasks.stars.detected_star import DetectedStar


def export_results(matched_candidates: list[DetectedStar], output_dir: Path):

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "star_detection_results.csv"

    with open(csv_path, mode="w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "id",
                "x_pixel",
                "y_pixel",
                "ra_deg",
                "dec_deg",
                "flux",
                "magnitude_obs",
                "object_id",
                "otype",
                "deviation_arcsec",
                *[f"mag_{f.lower()}_simbad" for f in FILTERS],
            ]
        )

        for i, candidate in enumerate(matched_candidates):
            writer.writerow(
                [
                    i,
                    candidate.x,
                    candidate.y,
                    candidate.coord.ra.deg,
                    candidate.coord.dec.deg,
                    candidate.flux,
                    candidate.magnitude_obs,
                    candidate.object_id,
                    candidate.otype,
                    candidate.deviation_arcsec,
                    *[getattr(candidate, f"mag_{f.lower()}") for f in FILTERS],
                ]
            )

    print(f"Star detection results exported to {csv_path}")