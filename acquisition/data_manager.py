from astropy.io import fits
from astropy import units as unit
from astropy.coordinates import SkyCoord


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

    def get_coordinates(self, fits_image):
        if fits_image is None:
            return None
        try:
            header = fits_image[0].header
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
