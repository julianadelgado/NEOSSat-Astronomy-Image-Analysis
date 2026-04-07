import csv
from pathlib import Path

import astropy.units as units
from astropy.coordinates import SkyCoord
from astroquery.simbad import Simbad
import numpy.ma as ma

import tasks.stars.identified_object as identified_object


def query_simbad(coord_string: str, radius: str, output_csv_path: Path = None):
    try:
        ra_str, dec_str = coord_string.split()
        ra_deg = float(ra_str)
        dec_deg = float(dec_str)
        coord = SkyCoord(ra=ra_deg * units.deg, dec=dec_deg * units.deg, frame="icrs")

        custom_simbad = Simbad()
        custom_simbad.add_votable_fields("otype")
        result = custom_simbad.query_region(coord, radius=radius)

        if result is None or len(result) == 0:
            print(f"Aucun objet trouvé pour {coord_string}")
            return None

        obj_coords = SkyCoord(ra=result["ra"], dec=result["dec"], unit=units.deg)
        separations = coord.separation(obj_coords)
        idx = separations.argmin()
        best_match = result[idx]
        distance = separations[idx].arcsec
        otype = best_match["otype"] if "otype" in result.colnames else "Unknown"

        obj = identified_object.IdentifiedObject(
            object_id=best_match["main_id"],
            ra_deg=best_match["ra"],
            dec_deg=best_match["dec"],
            distance_arcsec=distance,
            otype=otype,
        )

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
            print(f"Résultat SIMBAD exporté vers {output_csv_path}")

        return obj

    except Exception as e:
        print(f"Erreur pour {coord_string}: {e}")
        import traceback

        traceback.print_exc()


def query_simbad_skycoord(center: SkyCoord, radius, output_csv_path: Path = None):
    try:
        custom_simbad = Simbad()
        custom_simbad.add_votable_fields("otype", "B", "V", "R")
        result = custom_simbad.query_region(center, radius=radius)

        if result is None or len(result) == 0:
            print("No objects found for this region.")
            return []

        obj_coords = SkyCoord(ra=result["ra"], dec=result["dec"], unit=units.deg)

        objects = []
        csv_rows = []

        for i in range(len(result)):
            mag_b = result["B"][i] if "B" in result.colnames else None
            mag_v = result["V"][i] if "V" in result.colnames else None
            mag_r = result["R"][i] if "R" in result.colnames else None

            if all(m is None or ma.is_masked(m) for m in [mag_b, mag_v, mag_r]):
                continue

            otype = result["otype"][i] if "otype" in result.colnames else "Unknown"

            mag_b_val = None if mag_b is None or ma.is_masked(mag_b) else mag_b
            mag_v_val = None if mag_v is None or ma.is_masked(mag_v) else mag_v
            mag_r_val = None if mag_r is None or ma.is_masked(mag_r) else mag_r

            obj = identified_object.IdentifiedObjectSkyCoord(
                object_id=result["main_id"][i],
                coord=obj_coords[i],
                otype=otype,
                mag_b_val=mag_b_val,
                mag_v_val=mag_v_val,
                mag_r_val=mag_r_val
            )
            objects.append(obj)

            csv_rows.append([
                obj.object_id,
                obj.otype,
                obj.coord.ra.deg,
                obj.coord.dec.deg,
                mag_b_val,
                mag_v_val,
                mag_r_val
            ])

        if output_csv_path and csv_rows:
            output_csv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["main_id", "otype", "ra_deg", "dec_deg", "mag_b", "mag_v", "mag_r"])
                writer.writerows(csv_rows)
            print(f"SIMBAD query results saved as {output_csv_path}")

        return objects

    except Exception as e:
        print(f"Error query_simbad_skycoord: {e}")
        import traceback
        traceback.print_exc()
        return []
