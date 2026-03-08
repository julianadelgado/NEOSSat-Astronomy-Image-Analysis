import os

import numpy as np
from astropy import units as unit
from astropy.coordinates import SkyCoord
from astropy.io import fits
from PIL import Image


class DataManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.fits_image = self.load_fits_image(file_path)

    def load_fits_image(self, file_path):
        try:
            return fits.open(file_path)
        except Exception as e:
            print(f"Error loading FITS image: {e}")
            return None

    def get_coordinates(self):
        if self.fits_image is None:
            return None
        try:
            header = self.fits_image[0].header
            ra = header.get("RA") or header.get("OBJRA") or header.get("RA_DEG")
            dec = header.get("DEC") or header.get("OBJDEC") or header.get("DEC_DEG")

            if ra is not None and dec is not None:
                coord_unit = (
                    (unit.deg, unit.deg)
                    if isinstance(ra, (float, int))
                    else (unit.hourangle, unit.deg)
                )
                return SkyCoord(ra, dec, unit=coord_unit)
            else:
                print("Coordinates not found in common metadata keys.")
                return None
        except Exception as e:
            print(f"Error retrieving coordinates: {e}")
            return None

    def get_images_same_date(self):
        if self.fits_image is None:
            return None
        try:
            header = self.fits_image[0].header
            date_obs = header.get("DATE-OBS") or header.get("DATE")
            if date_obs is None:
                print("Observation date not found in metadata.")
                return None
            else:
                return date_obs.split("T")[0]
        except Exception as e:
            print(f"Error retrieving images by date: {e}")
            return {}

    def fits_to_png(self, output_path):
        if self.fits_image is None:
            return
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            data = self.fits_image[0].data
            data = (data - np.min(data)) / (np.max(data) - np.min(data)) * 255
            image = Image.fromarray(data.astype(np.uint8))
            image.save(output_path)

            print(f"FITS image converted to PNG and saved at: {output_path}")
        except Exception as e:
            print(f"Error converting FITS to PNG: {e}")
