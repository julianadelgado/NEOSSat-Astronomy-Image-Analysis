from dataclasses import dataclass
from typing import Optional

from astropy.coordinates import SkyCoord


@dataclass
class DetectedStar:

    x: float
    y: float

    coord: SkyCoord

    flux: float
    magnitude_obs: Optional[float] = None

    object_id: Optional[str] = None
    otype: Optional[str] = None
    deviation_arcsec: Optional[float] = None

    mag_b: Optional[float] = None
    mag_v: Optional[float] = None
    mag_r: Optional[float] = None
    mag_j: Optional[float] = None
    mag_h: Optional[float] = None
    mag_k: Optional[float] = None

    def is_matched(self) -> bool:
        return self.object_id is not None
