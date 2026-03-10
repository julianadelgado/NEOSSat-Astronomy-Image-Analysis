from dataclasses import dataclass


@dataclass
class IdentifiedObject:
    object_id: str
    ra_deg: float
    dec_deg: float
    distance_arcsec: float
