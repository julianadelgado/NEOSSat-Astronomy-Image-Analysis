import astropy.units as units
import numpy.ma as ma
from astropy.coordinates import SkyCoord

import tasks.stars.catalog.identified_object as identified_object

MINIMUM_MAGNITUDE = 20.0
FILTERS = ["B", "V", "R", "J", "H", "K"]


def map_single_best_match(coord: SkyCoord, result):
    obj_coords = SkyCoord(ra=result["ra"], dec=result["dec"], unit=units.deg)

    separations = coord.separation(obj_coords)
    idx = separations.argmin()

    ra_arr = result["ra"]
    dec_arr = result["dec"]
    main_id_arr = result["main_id"]
    otype_arr = result["otype"] if "otype" in result.colnames else None

    best_match = {
        "ra": ra_arr[idx],
        "dec": dec_arr[idx],
        "main_id": main_id_arr[idx],
        "otype": otype_arr[idx] if otype_arr is not None else "Unknown",
    }

    distance = separations[idx].arcsec

    return identified_object.IdentifiedObject(
        object_id=best_match["main_id"],
        ra_deg=best_match["ra"],
        dec_deg=best_match["dec"],
        distance_arcsec=distance,
        otype=best_match["otype"],
    )


def map_skycoord_catalog(result, obj_coords):
    objects = []
    csv_rows = []

    for i in range(len(result)):

        mags = {f: result[f][i] if f in result.colnames else None for f in FILTERS}

        if all(
            m is None or ma.is_masked(m) or m > MINIMUM_MAGNITUDE for m in mags.values()
        ):
            continue

        otype = result["otype"][i] if "otype" in result.colnames else "Unknown"

        mags_clean = {
            f: None if m is None or ma.is_masked(m) else m for f, m in mags.items()
        }

        obj = identified_object.IdentifiedObjectSkyCoord(
            object_id=result["main_id"][i],
            coord=obj_coords[i],
            otype=otype,
            **{f"mag_{f.lower()}_val": mags_clean[f] for f in FILTERS},
        )

        objects.append(obj)

        csv_rows.append(
            [
                result["main_id"][i],
                otype,
                obj_coords[i].ra.deg,
                obj_coords[i].dec.deg,
                *[mags_clean[f] for f in FILTERS],
            ]
        )

    return objects, csv_rows
