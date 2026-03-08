import os
import shutil
from astroquery.cadc import Cadc
from astropy import units as unit
from astropy.utils.data import download_file

class FitsHandler:
    def __init__(self, sky_coord):
        self.sky_coord = sky_coord
        self.cadc = Cadc()

    def download_images_to_directory(self, directory):
        try:
            results = self.cadc.query_region(self.sky_coord, radius=0.1*unit.deg, collection='NEOSSAT')
            if len(results) == 0:
                print("No NEOSSat images found for these coordinates.")
                return

            # Filter for cord images
            mask = [('cord' in str(obs_id).lower()) for obs_id in results['observationID']]
            filtered_results = results[mask] if any(mask) else results
            
            # Limit to 100
            subset = filtered_results[:100]
            print(f"Found {len(subset)} matching NEOSSat images. Retrieving download links...")

            urls = self.cadc.get_data_urls(subset)

            for i, url in enumerate(urls):
                try:
                    obs_id = subset[i]['observationID']
                    filename = f"{obs_id}.fits"
                    output_file = os.path.join(directory, filename)
                    
                    if os.path.exists(output_file):
                        continue
                    
                    tmp_path = download_file(url, show_progress=False)
                    shutil.move(tmp_path, output_file)
                    
                except Exception as inner_e:
                    print(f"Failed to download image {i}: {inner_e}")
                   
            print(f"Download process complete in {directory}.")
            
        except Exception as e:
            print(f"Error during CADC operation: {e}")