import os
import astroalign as aa
from astropy.io import fits
import numpy as np
from PIL import Image
from core.data_manager import DataManager

class ImageStacking:
    def __init__(self, images_path, data_manager):
        self.images_path = images_path
        self.data_manager = data_manager
    
    def stack_images(self):
        images_same_date = self.data_manager.get_images_same_date(self.images_path)

        if not images_same_date:
            print("No images found to stack.")
            return
        
        output_dir = os.path.join(self.images_path, "stacked")
        os.makedirs(output_dir, exist_ok=True)
        
        date_obs = images_same_date[0][0].header.get('DATE-OBS').split('T')[0]

        data_arrays = []
        reference_data = None
        for counter, img in enumerate(images_same_date):
            time_obs = img[0].header.get('TIME-OBS', '00-00-00').split('.')[0].replace(':', '-')
            before_stack_path = os.path.join(self.images_path, "before", f"{date_obs}__{time_obs}__{counter}.png")
            self.data_manager.fits_to_png(before_stack_path)
            current_data =img[0].data.astype(np.float64)
            if reference_data is None:
                reference_data = current_data
                data_arrays.append(current_data)
            else:
                try:
                    aligned_image, footprint = aa.register(current_data, reference_data)
                    data_arrays.append(aligned_image)
                except Exception as e:
                    print(f"Error aligning image {counter}: {e}")

        if len(data_arrays) > 1:
            print(f"Stacking {len(images_same_date)} images for {date_obs}...")
            
            stacked_data = np.nanmax(data_arrays, axis=0)
            
            vmin, vmax = np.percentile(stacked_data, [1, 99.9])
            stacked_scaled = np.clip((stacked_data - vmin) / (vmax - vmin) * 255, 0, 255)
            stacked_output = stacked_scaled.astype(np.uint8)

            stacked_image = Image.fromarray(stacked_output)
            output_path = os.path.join(output_dir, f'stacked_{date_obs}.png')
            stacked_image.save(output_path)
            print(f"Stacked image saved: {output_path}")
        else:
            print(f"Only one image for date {date_obs}, skipping stacking.")