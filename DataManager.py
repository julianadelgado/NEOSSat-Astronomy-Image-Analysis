import os
import shutil
from astropy.io import fits
from astroquery.cadc import Cadc
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.utils.data import download_file

class DataDirectoryManager:
    def __init__(self, data_directory):
        self.data_directory = data_directory

    def check_data_directory(self):
        return os.path.exists(self.data_directory)

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
        if fits_image is None: return None
        try:
            header = fits_image[0].header
            ra = header.get('RA') or header.get('OBJRA') or header.get('RA_DEG')
            dec = header.get('DEC') or header.get('OBJDEC') or header.get('DEC_DEG')
            
            if ra is not None and dec is not None:
                unit = (u.deg, u.deg) if isinstance(ra, (float, int)) else (u.hourangle, u.deg)
                return SkyCoord(ra, dec, unit=unit)
            else:
                print("Coordinates not found in common metadata keys.")
                return None
        except Exception as e:
            print(f"Error retrieving coordinates: {e}")
            return None
        

class DownloadFitsImage:
    def __init__(self, sky_coord):
        self.sky_coord = sky_coord
        self.cadc = Cadc()

    def download_images_to_directory(self, directory):
        try:
            results = self.cadc.query_region(self.sky_coord, radius=0.1*u.deg, collection='NEOSSAT')
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
                    
                    tmp_path = download_file(url, cache=True, show_progress=False)
                    shutil.move(tmp_path, output_file)
                    
                except Exception as inner_e:
                    print(f"Failed to download image {i}: {inner_e}")
                   
            print(f"Download process complete in {directory}.")
            
        except Exception as e:
            print(f"Error during CADC operation: {e}")

def main():
    print("Welcome to the NEOSSat Astronomy Image Analysis!")
    while True:
        print("Select a valid directory containing the data you want to analyze:")
        data_directory = input("Enter the path to the data directory: ")
        manager = DataDirectoryManager(data_directory)
        if manager.check_data_directory():
            print(f"Data directory '{data_directory}' found.")
            break
        else:
            print(f"Data directory '{data_directory}' does not exist. Please try again.")
    
    for filename in os.listdir(data_directory):
        if filename.endswith('.fits'):
            file_path = os.path.join(data_directory, filename)
            print(f"\nProcessing: {filename}")
            
            data_manager = DataManager(file_path)
            sky_coord = data_manager.get_coordinates(data_manager.fits_image)
            
            if sky_coord:
                print(f"Coordinates Found: {sky_coord.to_string('hmsdms')}")
                
                clean_name = filename.replace('.fits', '')
                save_path = os.path.join(clean_name, "training")
                os.makedirs(save_path, exist_ok=True)
                
                downloader = DownloadFitsImage(sky_coord)
                downloader.download_images_to_directory(save_path)
            
            data_manager.fits_image.close()
        
if __name__ == '__main__':
    main()