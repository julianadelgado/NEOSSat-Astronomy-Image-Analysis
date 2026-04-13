import csv
from pathlib import Path

import astropy.units as units
from astropy.coordinates import SkyCoord

from services.simbad.simbad_client import (
    query_region_with_filters,
    query_region_with_otype,
)
from tasks.stars.catalog.simbad_mapper import (
    map_single_best_match,
    map_skycoord_catalog,
)


def query_simbad(coord_string: str, radius: str, output_csv_path: Path = None):
    try:
        ra_str, dec_str = coord_string.split()
        ra_deg = float(ra_str)
        dec_deg = float(dec_str)

        coord = SkyCoord(ra=ra_deg * units.deg, dec=dec_deg * units.deg, frame="icrs")

        result = query_region_with_otype(coord, radius)

        if result is None or len(result) == 0:
            print(f"Aucun objet trouvé pour {coord_string}")
            return None

        obj = map_single_best_match(coord, result)

        if output_csv_path:
            output_csv_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["main_id", "ra_deg", "dec_deg", "distance_arcsec", "otype"]
                )
                writer.writerow(
                    [
                        obj.object_id,
                        obj.ra_deg,
                        obj.dec_deg,
                        obj.distance_arcsec,
                        obj.otype,
                    ]
                )

        return obj

    except Exception as e:
        print(f"Erreur pour {coord_string}: {e}")
        import traceback

        traceback.print_exc()
        return None


def query_simbad_skycoord(center: SkyCoord, radius, output_csv_path: Path = None):
    try:
        FILTERS = ["B", "V", "R", "J", "H", "K"]

        result = query_region_with_filters(center, radius, FILTERS)

        if result is None or len(result) == 0:
            print("No objects found for this region.")
            return []

        obj_coords = SkyCoord(ra=result["ra"], dec=result["dec"], unit=units.deg)

        objects, csv_rows = map_skycoord_catalog(result, obj_coords)

        if output_csv_path and csv_rows:
            output_csv_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "main_id",
                        "otype",
                        "ra_deg",
                        "dec_deg",
                        "mag_b",
                        "mag_v",
                        "mag_r",
                        "mag_j",
                        "mag_h",
                        "mag_k",
                    ]
                )
                writer.writerows(csv_rows)

        return objects

    except Exception as e:
        print(f"Error query_simbad_skycoord: {e}")
        import traceback

        traceback.print_exc()
        return []
