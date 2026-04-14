from typing import List, Set, Tuple

from tasks.stars.detected_star import DetectedStar
from tasks.stars.catalog.identified_object import IdentifiedObjectSkyCoord


MAX_MATCH_RADIUS_ARCSEC = 30.0


def match_candidates(
    detected_candidates: List[DetectedStar],
    region_catalog: List[IdentifiedObjectSkyCoord],
) -> List[DetectedStar]:
    """
    Associate detected star candidates with catalog objects based on positional proximity.
    """

    if not detected_candidates or not region_catalog:
        return detected_candidates

    # -------------------------------------------
    # Source pairing based on angular separation
    # -------------------------------------------
    pairs: List[Tuple[int, int, float]] = []

    for i, star in enumerate(detected_candidates):
        for j, obj in enumerate(region_catalog):
            sep = star.coord.separation(obj.coord).arcsec
            if sep <= MAX_MATCH_RADIUS_ARCSEC:
                pairs.append((i, j, sep))

    pairs.sort(key=lambda x: x[2])

    matched_stars: Set[int] = set()
    used_catalog: Set[int] = set()

    # ---------------------------------------------------------------
    # Final matching - one-to-one association based on closest pairs
    # ---------------------------------------------------------------
    for star_idx, cat_idx, sep in pairs:
        if star_idx in matched_stars or cat_idx in used_catalog:
            continue

        star = detected_candidates[star_idx]
        obj = region_catalog[cat_idx]

        star.object_id = obj.object_id
        star.otype = obj.otype
        star.deviation_arcsec = sep

        star.mag_b = obj.mag_b_val
        star.mag_v = obj.mag_v_val
        star.mag_r = obj.mag_r_val
        star.mag_j = obj.mag_j_val
        star.mag_h = obj.mag_h_val
        star.mag_k = obj.mag_k_val

        matched_stars.add(star_idx)
        used_catalog.add(cat_idx)

    return detected_candidates
