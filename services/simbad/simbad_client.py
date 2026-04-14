from astropy.coordinates import SkyCoord
from astroquery.simbad import Simbad


def query_region(center: SkyCoord, radius):
    simbad = Simbad()
    return simbad.query_region(center, radius=radius)


def query_region_with_otype(center: SkyCoord, radius):
    simbad = Simbad()
    simbad.add_votable_fields("otype")
    return simbad.query_region(center, radius=radius)


def query_region_with_filters(center: SkyCoord, radius, filters):
    simbad = Simbad()
    simbad.add_votable_fields("otype", *filters)
    return simbad.query_region(center, radius=radius)
