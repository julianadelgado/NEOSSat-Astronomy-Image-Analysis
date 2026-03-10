import os
import random
import time
import urllib.request
import numpy as np

try:
    from astroquery.cadc import Cadc
    from astropy.coordinates import SkyCoord
    from astropy import units as u
except ImportError:
    print("Missing requirements. Please install via: pip install astropy astroquery numpy")
    exit(1)

def generate_random_coords(num_coords=1):
    """
    Generates a specified number of random coordinates on the celestial sphere.
    Avoids clustering at poles by using a uniform distribution on a sphere.
    """
    coords = []
    for _ in range(num_coords):
        ra = random.uniform(0, 360) # Right ascension 0-360 degrees
        dec = np.degrees(np.arcsin(random.uniform(-1, 1))) # Declination -90 to +90 degrees uniformly
        coords.append(SkyCoord(ra=ra, dec=dec, unit=(u.deg, u.deg)))
    return coords

def download_neossat_from_random_coords(target_count=2000, output_dir='dataset', max_attempts=5000):
    """
    Method 1: Searches true random coordinates across the sky for NEOSSat images.
    Note: Since NEOSSat only observes very specific targets (asteroids, satellites, etc.), 
    most random coordinate queries will return 0 results. This method can be extremely slow.
    """
    os.makedirs(output_dir, exist_ok=True)
    cadc = Cadc()
    
    downloaded_files = set(f for f in os.listdir(output_dir) if f.endswith('.fits') or f.endswith('.fits.fz'))
    downloaded_count = len(downloaded_files)
    
    attempts = 0
    print(f"Starting true random coordinate search. Target: {target_count} images.")
    
    while downloaded_count < target_count and attempts < max_attempts:
        coord = generate_random_coords(1)[0]
        attempts += 1
        
        # Searching 1 degree radius (FOV of NEOSSat is roughly 0.85 degrees)
        try:
            results = cadc.query_region(coord, radius=0.85 * u.deg, collection='NEOSSAT')
        except Exception as e:
            time.sleep(1) # Back off on error
            continue
            
        if results is None or len(results) == 0:
            if attempts % 50 == 0:
                print(f"Checked {attempts} random locations. Found nothing so far. ({downloaded_count}/{target_count} downloaded)")
            continue
            
        print(f"Found {len(results)} images at RA={coord.ra.deg:.2f}, DEC={coord.dec.deg:.2f}!")
        
        try:
            urls = cadc.get_data_urls(results)
            for url in urls:
                if downloaded_count >= target_count: break
                if not isinstance(url, str): continue
                
                filename = url.split('/')[-1].split('?')[0]
                if not filename.endswith('.fits') and not filename.endswith('.fits.fz'):
                    filename += '.fits'
                    
                filepath = os.path.join(output_dir, filename)
                if not os.path.exists(filepath):
                    print(f"[{downloaded_count+1}/{target_count}] Downloading {filename}...")
                    urllib.request.urlretrieve(url, filepath)
                    downloaded_count += 1
                    time.sleep(0.5)
        except Exception as e:
            print(f"Error handling URLs: {e}")

    print(f"Finished random coordinate search. Downloaded {downloaded_count}/{target_count} images in {attempts} locations.")


def download_neossat_random_sample(target_count=2000, output_dir='dataset'):
    """
    Method 2 (Recommended): Queries the CADC for thousands of available NEOSSat observations, 
    shuffles them, and downloads a random subset. 
    This is hundreds of times faster than searching random sky coordinates.
    """
    os.makedirs(output_dir, exist_ok=True)
    cadc = Cadc()
    
    print("Querying CADC for available NEOSSat images...")
    query = """
        SELECT TOP 20000 
            *
        FROM caom2.Plane AS p
        JOIN caom2.Observation AS o ON p.obsID = o.obsID
        WHERE o.collection = 'NEOSSAT' AND p.dataProductType = 'image'
    """
    
    try:
        results = cadc.exec_sync(query)
        print(f"Found {len(results)} NEOSSAT image records.")
    except Exception as e:
        print(f"Failed to query CADC: {e}")
        return

    # Randomly select records
    if len(results) > target_count:
        indices = random.sample(range(len(results)), target_count)
        sampled_results = results[indices]
    else:
        sampled_results = results

    # Fetch data URLs in small batches to prevent timeout/hangs and missing columns
    print(f"Attempting to download {len(sampled_results)} random images...")
    
    downloaded_count = 0
    batch_size = 50
    
    for i in range(0, len(sampled_results), batch_size):
        batch = sampled_results[i:i+batch_size]
        try:
            urls = cadc.get_data_urls(batch)
        except Exception as e:
            print(f"Failed to get data URLs for batch {i//batch_size}: {e}")
            continue

        for url in urls:
            if downloaded_count >= target_count: break
            if not isinstance(url, str): continue
            
            filename = url.split('/')[-1].split('?')[0]
            if not filename.endswith('.fits') and not filename.endswith('.fits.fz'):
                filename += '.fits'
                
            filepath = os.path.join(output_dir, filename)
            
            try:
                if not os.path.exists(filepath):
                    print(f"[{downloaded_count+1}/{target_count}] Downloading {filename}...")
                    urllib.request.urlretrieve(url, filepath)
                    time.sleep(0.2)
                else:
                    print(f"[{downloaded_count+1}/{target_count}] File {filename} already exists, skipping.")
                downloaded_count += 1
            except Exception as e:
                print(f"Failed to download {filename}: {e}")

    print(f"\nFinished processing. Total dataset size: {downloaded_count} images downloaded to '{output_dir}'.")

if __name__ == '__main__':
    # You can choose between true random coordinates (very slow) 
    # or querying CADC and grabbing a random sample of images (very fast).
    
    METHOD = 'sample' # Change to 'coordinates' if you strictly want to search blind coordinates
    
    print(f"Initializing NEOSSAT downloader using '{METHOD}' method...")
    if METHOD == 'coordinates':
        download_neossat_from_random_coords(target_count=2000, output_dir='dataset')
    else:
        download_neossat_random_sample(target_count=2000, output_dir='dataset')
