from typing import List, Tuple

import numpy as np
from astropy.wcs import WCS

from tasks.stars.detected_star import DetectedStar
from tasks.stars.catalog.identified_object import IdentifiedObjectSkyCoord
from typing import cast
from astropy.coordinates import SkyCoord
from scipy.ndimage import shift as nd_shift

MAX_SEARCH_RADIUS_PX = 50
MIN_MATCHES_REQUIRED = 5


def estimate_global_shift(
    detected: List[DetectedStar],
    catalog: List[IdentifiedObjectSkyCoord],
    wcs: WCS,
) -> Tuple[float, float]:
    """
    Compute the global shift (dx, dy) to align detected stars with catalog objects.
    """

    if not detected or not catalog:
        return 0.0, 0.0

    # ----------------------------------------------------------
    # Catalog conversion to pixel coordinates
    # ----------------------------------------------------------
    catalog_pixels = []
    for obj in catalog:
        try:
            x, y = wcs.world_to_pixel(obj.coord)
            catalog_pixels.append((x, y))
        except Exception:
            continue

    if len(catalog_pixels) == 0:
        return 0.0, 0.0

    catalog_pixels = np.array(catalog_pixels)

    shifts = []

    # ----------------------------------------------------------
    # Offset vector estimation
    # ----------------------------------------------------------
    for star in detected:
        dx = catalog_pixels[:, 0] - star.x
        dy = catalog_pixels[:, 1] - star.y

        dist = np.sqrt(dx**2 + dy**2)

        mask = dist < MAX_SEARCH_RADIUS_PX

        if not np.any(mask):
            continue

        idx = np.argmin(dist)
        shifts.append((dx[idx], dy[idx]))

    if len(shifts) < MIN_MATCHES_REQUIRED:
        print("[ALIGN] Not enough matches to estimate shift")
        return 0.0, 0.0

    shifts = np.array(shifts)

    dx_median = np.median(shifts[:, 0])
    dy_median = np.median(shifts[:, 1])

    print(f"[ALIGN] Estimated shift: dx={dx_median:.2f}, dy={dy_median:.2f}")

    return float(dx_median), float(dy_median)


def apply_shift(
    detected: List[DetectedStar],
    wcs: WCS,
    dx: float,
    dy: float,
) -> List[DetectedStar]:
    """
    Apply the computed shift to the detected stars and update their world coordinates accordingly.
    """

    for star in detected:
        star.x += dx
        star.y += dy

        star.coord = cast(SkyCoord, wcs.pixel_to_world(star.x, star.y))

    return detected


def apply_shift_to_image(
    image: np.ndarray,
    dx: float,
    dy: float,
) -> np.ndarray:
    """
    Apply the computed shift to the image using interpolation.
    """

    shifted_image = nd_shift(
        image,
        shift=(dy, dx),
        order=1,
        mode="constant",
        cval=0.0,
    )

    return shifted_image


def align_detected_to_catalog_with_image(
    detected,
    catalog,
    wcs,
    image,
):
    """
    Align detected stars to catalog objects by estimating and applying a global shift.
    """

    dx, dy = estimate_global_shift(detected, catalog, wcs)

    if dx == 0.0 and dy == 0.0:
        print("[ALIGN] No correction applied")
        return detected, image

    detected = apply_shift(detected, wcs, dx, dy)
    image = apply_shift_to_image(image, dx, dy)

    return detected, image
