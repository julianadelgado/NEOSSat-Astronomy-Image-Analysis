import csv
from pathlib import Path

from astropy.coordinates import SkyCoord

from tasks.stars.constants import FILTERS
from tasks.stars.detected_star import DetectedStar
from tasks.stars.exports.csv_exporter import export_results


def make_star(i=0):
    coord = SkyCoord(ra=10 + i, dec=20 + i, unit="deg")

    star = DetectedStar(
        x=float(i),
        y=float(i + 1),
        coord=coord,
        flux=100.0 + i,
        magnitude_obs=15.0 + i,
        object_id=f"OBJ_{i}",
        otype="STAR",
        deviation_arcsec=0.1 * i,
        mag_b=10.0 + i,
        mag_v=11.0 + i,
        mag_r=12.0 + i,
        mag_j=13.0 + i,
        mag_h=14.0 + i,
        mag_k=15.0 + i,
    )

    return star


def test_export_results_creates_csv(tmp_path: Path):
    stars = [make_star(0), make_star(1)]

    export_results(stars, tmp_path)

    csv_path = tmp_path / "star_detection_results.csv"

    assert csv_path.exists()

    with open(csv_path, newline="") as f:
        reader = list(csv.reader(f))

    assert len(reader) == 3

    header = reader[0]
    rows = reader[1:]

    assert header[:10] == [
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
    ]

    expected_filter_cols = [f"mag_{f.lower()}_simbad" for f in FILTERS]
    assert header[10:] == expected_filter_cols

    assert rows[0][1] == "0.0"
    assert rows[0][7] == "OBJ_0"


def test_export_results_empty(tmp_path: Path):
    export_results([], tmp_path)

    csv_path = tmp_path / "star_detection_results.csv"

    assert csv_path.exists()

    with open(csv_path, newline="") as f:
        reader = list(csv.reader(f))

    assert len(reader) == 1


def test_export_results_creates_directory(tmp_path: Path):
    nested_dir = tmp_path / "a" / "b" / "c"

    stars = [make_star(0)]

    export_results(stars, nested_dir)

    csv_path = nested_dir / "star_detection_results.csv"

    assert nested_dir.exists()
    assert csv_path.exists()
