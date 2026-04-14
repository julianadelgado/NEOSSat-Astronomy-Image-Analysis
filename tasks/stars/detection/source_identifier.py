from typing import List

import numpy as np
from astropy.stats import sigma_clipped_stats

from tasks.stars.constants import (
    SATURATION_PERCENTILE,
    SIGMA,
)
from tasks.stars.detected_star import DetectedStar

from scipy.ndimage import label, center_of_mass

from tasks.stars.constants import SATURATION_PERCENTILE, SIGMA

MAX_MATCH_RADIUS_ARCSEC = 3.0


def detect_sources(image: np.ndarray, wcs, header) -> List[DetectedStar]:

    # refactorised using blob based-detection for better handling of saturated stars and already filtered source images (CORD).
    # AB - 13/04/2026

    mean, median, std = sigma_clipped_stats(image, sigma=SIGMA)

    exptime = header.get("EXPOSURE", header.get("AEXPTIME", 1.0))
    gain = float(header.get("GAIN", 1.0))
    zp = 25.0

    detected_candidates: List[DetectedStar] = []

    # ------------------------------------------------------------------
    # 1. Threshold-based detection (blob method)
    # ------------------------------------------------------------------

    threshold = np.percentile(image, 99.6)
    binary = image > threshold

    labeled, n_objects = label(binary)

    for i in range(1, n_objects + 1):
        mask = labeled == i

        if np.sum(mask) < 3:
            continue

        y_c, x_c = center_of_mass(mask)

        flux_sum = float(np.sum(image[mask]))

        try:
            magnitude = -2.5 * np.log10((flux_sum / exptime) * gain) + zp
        except Exception:
            magnitude = None

        world_coord = wcs.pixel_to_world(x_c, y_c)

        detected_candidates.append(
            DetectedStar(
                x=float(x_c),
                y=float(y_c),
                coord=world_coord,
                flux=flux_sum,
                magnitude_obs=float(magnitude) if magnitude is not None else None,
            )
        )

    # ------------------------------------------------------------------
    # 2. Saturation handling for bright stars
    # ------------------------------------------------------------------
    saturation_threshold = np.percentile(image, SATURATION_PERCENTILE)
    saturated_mask = image >= saturation_threshold

    if np.any(saturated_mask):
        labeled_sat, n_sat = label(saturated_mask)

        for i in range(1, n_sat + 1):
            mask = labeled_sat == i

            if np.sum(mask) < 3:
                continue

            y_c, x_c = center_of_mass(mask)

            flux_sum = float(np.sum(image[mask]))

            try:
                magnitude = -2.5 * np.log10((flux_sum / exptime) * gain) + zp
            except Exception:
                magnitude = None

            world_coord = wcs.pixel_to_world(x_c, y_c)

            detected_candidates.append(
                DetectedStar(
                    x=float(x_c),
                    y=float(y_c),
                    coord=world_coord,
                    flux=flux_sum,
                    magnitude_obs=float(magnitude) if magnitude is not None else None,
                )
            )

    print(f"Stars detected (blob method): {len(detected_candidates)}")

    return detected_candidates
