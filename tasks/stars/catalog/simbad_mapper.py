import numpy.ma as ma
import astropy.units as units
from astropy.coordinates import SkyCoord

import tasks.stars.catalog.identified_object as identified_object

MINIMUM_MAGNITUDE = 20.0
FILTERS = ["B", "V", "R", "J", "H", "K"]


def map_single_best_match(coord: SkyCoord, result):
    obj_coords = SkyCoord(ra=result["ra"], dec=result["dec"], unit=units.deg)

    separations = coord.separation(obj_coords)
    idx = separations.argmin()

    best_match = result[idx]
    distance = separations[idx].arcsec

    otype = best_match["otype"] if "otype" in result.colnames else "Unknown"

    return identified_object.IdentifiedObject(
        object_id=best_match["main_id"],
        ra_deg=best_match["ra"],
        dec_deg=best_match["dec"],
        distance_arcsec=distance,
        otype=otype,
    )


def map_skycoord_catalog(result, obj_coords):
    objects = []
    csv_rows = []

    for i in range(len(result)):

        mags = {
            f: result[f][i] if f in result.colnames else None
            for f in FILTERS
        }

        if all(
            m is None or ma.is_masked(m) or m > MINIMUM_MAGNITUDE
            for m in mags.values()
        ):
            continue

        otype = result["otype"][i] if "otype" in result.colnames else "Unknown"

        mags_clean = {
            f: None if m is None or ma.is_masked(m) else m
            for f, m in mags.items()
        }

        obj = identified_object.IdentifiedObjectSkyCoord(
            object_id=result["main_id"][i],
            coord=obj_coords[i],
            otype=otype,
            **{f"mag_{f.lower()}_val": mags_clean[f] for f in FILTERS}
        )

        objects.append(obj)

        csv_rows.append([
            result["main_id"][i],
            otype,
            obj_coords[i].ra.deg,
            obj_coords[i].dec.deg,
            *[mags_clean[f] for f in FILTERS]
        ])

    return objects, csv_rows
