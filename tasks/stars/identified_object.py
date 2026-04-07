from dataclasses import dataclass

from astropy.coordinates import SkyCoord


@dataclass
class IdentifiedObject:
    object_id: str
    ra_deg: float
    dec_deg: float
    distance_arcsec: float
    otype: str


@dataclass
class IdentifiedObjectSkyCoord:
    object_id: str
    coord: SkyCoord
    otype: str
    mag_b_val: float = None
    mag_v_val: float = None
    mag_r_val: float = None
