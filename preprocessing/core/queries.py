from astroquery.simbad import Simbad
from astropy.coordinates import SkyCoord
import astropy.units as units
from preprocessing.core.identifiedObject import IdentifiedObject

def query_simbad(coord_string, radius):

    try:
        ra_str, dec_str = coord_string.split()
        ra_deg = float(ra_str)
        dec_deg = float(dec_str)
        coord = SkyCoord(ra=ra_deg*units.deg, dec=dec_deg*units.deg, frame='icrs')
        result = Simbad.query_region(coord, radius=f'{radius}')

        if result is None or len(result) == 0:
            return None
        else:

            obj_coords = SkyCoord(
                ra=result["ra"],
                dec=result["dec"],
                unit=(units.hourangle, units.deg)
            )

            separations = coord.separation(obj_coords)

            idx = separations.argmin()

            best_match = result[idx]

            distance = separations[idx].arcsec

            return IdentifiedObject(
                object_id=best_match["main_id"],
                ra_deg=best_match["ra"],
                dec_deg=best_match["dec"],
                distance_arcsec=distance
            )
    except Exception as e:
        print(f"Erreur pour {coord_string}: {e}")
        import traceback
        traceback.print_exc()
