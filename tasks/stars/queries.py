import csv
from pathlib import Path

import astropy.units as units
from astropy.coordinates import SkyCoord
from astroquery.simbad import Simbad

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
        custom_simbad.add_votable_fields("otype")
        result = custom_simbad.query_region(center, radius=radius)

        if result is None or len(result) == 0:
            print("Aucun objet trouvé dans la région.")
            return []

        obj_coords = SkyCoord(ra=result["ra"], dec=result["dec"], unit=units.deg)

        objects = []
        for i in range(len(result)):
            otype = result["otype"][i] if "otype" in result.colnames else "Unknown"
            objects.append(
                identified_object.IdentifiedObjectSkyCoord(
                    object_id=result["main_id"][i], coord=obj_coords[i], otype=otype
                )
            )

        if output_csv_path:
            output_csv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["main_id", "otype", "ra_deg", "dec_deg"])
                for obj in objects:
                    writer.writerow(
                        [obj.object_id, obj.otype, obj.coord.ra.deg, obj.coord.dec.deg]
                    )
            print(f"Résultats SIMBAD exportés vers {output_csv_path}")

        return objects

    except Exception as e:
        print(f"Erreur query_simbad_skycoord: {e}")
        import traceback

        traceback.print_exc()
        return []
