import numpy as np
from astropy.coordinates import SkyCoord
from astropy.stats import sigma_clipped_stats
from photutils.detection import DAOStarFinder
from sklearn.cluster import DBSCAN
from tasks.stars.constants import (
    SIGMA,
    DAO_FINDER_FWHM,
    DAO_FINDER_THRESHOLD,
    CLUSTER_EPS,
    SATURATION_PERCENTILE,
    MATCH_THRESHOLD_DEFAULT,
    MATCH_THRESHOLD_BRIGHT,
    CANDIDATE_NOT_FOUND_STRING,
    FILTERS,
)


def detect_sources(image: np.ndarray, wcs, header):

    mean, median, std = sigma_clipped_stats(image, sigma=SIGMA)
    daofind = DAOStarFinder(fwhm=DAO_FINDER_FWHM, threshold=DAO_FINDER_THRESHOLD * std)

    sources = daofind(image - median)
    detected_candidates = []

    if sources is None or len(sources) == 0:
        print("DAOStarFinder - No sources found.")
        return []

    exptime = header.get("EXPOSURE", header.get("AEXPTIME", 1.0))
    gain = float(header.get("GAIN", 1.0))
    zp = 25.0

    x_coord = sources["xcentroid"]
    y_coord = sources["ycentroid"]
    flux = sources["flux"]

    coords_array = np.column_stack((x_coord, y_coord))
    clustering = DBSCAN(eps=CLUSTER_EPS, min_samples=1).fit(coords_array)

    for cluster_label in np.unique(clustering.labels_):
        cluster_indices = np.where(clustering.labels_ == cluster_label)[0]
        x_mean = np.mean(x_coord[cluster_indices])
        y_mean = np.mean(y_coord[cluster_indices])
        flux_sum = np.sum(flux[cluster_indices])
        world_coord = wcs.pixel_to_world(x_mean, y_mean)

        try:
            magnitude = -2.5 * np.log10(flux_sum / exptime * gain) + zp
        except:
            magnitude = None

        detected_candidates.append(
            {
                "x": float(x_mean),
                "y": float(y_mean),
                "coord": world_coord,
                "flux": float(flux_sum),
                "magnitude": float(magnitude) if magnitude is not None else None,
                "saturated": False,
            }
        )

    saturation_threshold = np.percentile(image, SATURATION_PERCENTILE)
    saturated_mask = image >= saturation_threshold

    if np.any(saturated_mask):
        from scipy.ndimage import label, center_of_mass

        labeled, n_objects = label(saturated_mask)
        for i in range(1, n_objects + 1):
            mask_i = labeled == i
            y_c, x_c = center_of_mass(mask_i)
            world_coord = wcs.pixel_to_world(x_c, y_c)
            flux_sum = np.sum(image[mask_i])

            try:
                magnitude = -2.5 * np.log10(flux_sum / exptime * gain) + zp
            except:
                magnitude = None

            detected_candidates.append(
                {
                    "x": float(x_c),
                    "y": float(y_c),
                    "coord": world_coord,
                    "flux": float(flux_sum),
                    "magnitude": float(magnitude) if magnitude is not None else None,
                    "saturated": True,
                }
            )

    print(f"Stars detected: {len(detected_candidates)}")
    return detected_candidates


def match_candidates(detected_candidates, region_catalog):

    if len(detected_candidates) == 0:
        return []

    if len(region_catalog) == 0:
        return [
            {
                **src,
                "object_id": CANDIDATE_NOT_FOUND_STRING,
                "otype": "Default",
                "deviation_arcsec": None,
                **{f"sim_{f.lower()}": None for f in FILTERS},
            }
            for src in detected_candidates
        ]

    detected_coords = SkyCoord([src["coord"] for src in detected_candidates])
    catalog_coords = SkyCoord([obj.coord for obj in region_catalog])

    idx, sep2d, _ = detected_coords.match_to_catalog_sky(catalog_coords)

    matched_candidates = []
    magnitudes_obs = []

    for i, src in enumerate(detected_candidates):

        sep_threshold = MATCH_THRESHOLD_BRIGHT if src["flux"] > np.percentile([c["flux"] for c in detected_candidates], 99) else MATCH_THRESHOLD_DEFAULT
        separation = sep2d[i]

        if separation < sep_threshold:
            matched_obj = region_catalog[idx[i]]
            matched_candidates.append({
                **src,
                "object_id": matched_obj.object_id,
                "otype": getattr(matched_obj, "otype", "Default"),
                "deviation_arcsec": separation.arcsec,
                **{
                    f"sim_{f.lower()}": getattr(matched_obj, f"mag_{f.lower()}_val", None)
                    for f in FILTERS
                },
            })
        else:
            matched_candidates.append({
                **src,
                "object_id": CANDIDATE_NOT_FOUND_STRING,
                "otype": "Default",
                "deviation_arcsec": separation.arcsec,
                **{f"sim_{f.lower()}": None for f in FILTERS},
            })

        if src.get("magnitude") is not None:
            magnitudes_obs.append(src["magnitude"])

    if magnitudes_obs:
        print(f"Observed magnitudes: min={min(magnitudes_obs):.2f}, max={max(magnitudes_obs):.2f}")

    sim_mags = [obj.mag_v_val for obj in region_catalog if obj.mag_v_val is not None]
    if sim_mags:
        print(f"SIMBAD catalog magnitudes (V): min={min(sim_mags):.2f}, max={max(sim_mags):.2f}")
        print(f"Number of expected stars in frame: {len(sim_mags)}")

    print(f"Matched {sum(1 for c in matched_candidates if c['object_id'] != CANDIDATE_NOT_FOUND_STRING)} candidates with catalog objects.")

    return matched_candidates
