import os
import shutil

import numpy as np
from astropy import units as unit
from astropy.time import Time
from astropy.utils.data import download_file
from astroquery.cadc import Cadc


class FitsHandler:
    def __init__(self, sky_coord, date_obs):
        self.sky_coord = sky_coord
        self.date_obs = date_obs
        self.cadc = Cadc()

    def download_images_to_directory(self, directory):
        try:
            if self.date_obs is None:
                print(
                    "Observation date is not available. Cannot filter images by date."
                )
                return

            t = Time(self.date_obs)
            year = t.datetime.year
            day_of_year = t.datetime.timetuple().tm_yday
            search_date_doy = f"{year}{day_of_year:03d}"

            results = self.cadc.query_region(
                self.sky_coord, radius=0.1 * unit.deg, collection="NEOSSAT"
            )
            if len(results) == 0:
                print("No NEOSSat images found for these coordinates.")
                return

            # Filter for the specific observation date
            mask_date = [
                search_date_doy in str(obs_id) for obs_id in results["observationID"]
            ]
            results_filtered_date = results[mask_date]

            if len(results_filtered_date) == 0:
                print(f"No NEOSSat images found for the date {self.date_obs}.")
                return

            # Filter for cord images
            mask = [
                ("cord" in str(obs_id).lower())
                for obs_id in results_filtered_date["observationID"]
            ]
            filtered_results = (
                results_filtered_date[mask] if any(mask) else results_filtered_date
            )

            # Limit to 100
            subset = filtered_results[:100]
            print(
                f"Found {len(subset)} matching NEOSSat images. Retrieving download links..."
            )

            urls = self.cadc.get_data_urls(subset)

            for i, url in enumerate(urls):
                try:
                    obs_id = subset[i]["observationID"]
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
