import numpy as np
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS


def get_image_region(image: np.ndarray, wcs: WCS):

    height, width = image.shape
    x_corners = [0, width, 0, width]
    y_corners = [0, 0, height, height]

    corner_coords = wcs.pixel_to_world(x_corners, y_corners)

    center = SkyCoord(ra=np.mean(corner_coords.ra), dec=np.mean(corner_coords.dec))

    print(
        f"Image region center: RA={center.ra.deg:.4f} deg, Dec={center.dec.deg:.4f} deg"
    )

    separations = center.separation(corner_coords)
    radius = separations.max()

    print(f"Image region radius: {radius.arcmin:.2f} arcmin")

    return center, radius
