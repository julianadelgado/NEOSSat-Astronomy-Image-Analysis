import numpy as np
from astropy.stats import sigma_clipped_stats
from photutils.detection import DAOStarFinder
from sklearn.cluster import DBSCAN
from tasks.stars.constants import (
    SIGMA,
    DAO_FINDER_FWHM,
    DAO_FINDER_THRESHOLD,
    CLUSTER_EPS,
    SATURATION_PERCENTILE,
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
