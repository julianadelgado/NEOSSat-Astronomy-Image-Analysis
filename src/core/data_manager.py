import os
from astropy.io import fits
from astropy import units as unit
from astropy.coordinates import SkyCoord
import numpy as np
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
        if self.fits_image is None: return None
        try:
            header = self.fits_image[0].header
            ra = header.get('RA') or header.get('OBJRA') or header.get('RA_DEG')
            dec = header.get('DEC') or header.get('OBJDEC') or header.get('DEC_DEG')
            
            if ra is not None and dec is not None:
                coord_unit = (unit.deg, unit.deg) if isinstance(ra, (float, int)) else (unit.hourangle, unit.deg)
                return SkyCoord(ra, dec, unit=coord_unit)
            else:
                print("Coordinates not found in common metadata keys.")
                return None
        except Exception as e:
            print(f"Error retrieving coordinates: {e}")
            return None
        
    def get_images_same_date(self, all_images_path):
        try:
            current_header = self.fits_image[0].header
            current_date_obs = current_header.get('DATE-OBS')
            current_date_obs = current_date_obs.split('T')[0]
            images_same_date = []
            for filename in os.listdir(all_images_path):
                if filename.endswith('.fits'):
                    img = fits.open(os.path.join(all_images_path, filename))
                    date_obs = img[0].header.get('DATE-OBS')
                    date_obs = date_obs.split('T')[0]
                    if current_date_obs == date_obs:
                        images_same_date.append(img)
            return images_same_date
        except Exception as e:
            print(f"Error retrieving images by date: {e}")
            return {}

    def fits_to_png(self, output_path):
        if self.fits_image is None: return
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            data = self.fits_image[0].data
            data = (data - np.min(data)) / (np.max(data) - np.min(data)) * 255
            image = Image.fromarray(data.astype(np.uint8))
            image.save(output_path)

            print(f"FITS image converted to PNG and saved at: {output_path}")
        except Exception as e:
            print(f"Error converting FITS to PNG: {e}")

