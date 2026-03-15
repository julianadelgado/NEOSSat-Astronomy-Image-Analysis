import os
import shutil

from acquisition.data_manager import DataManager
from acquisition.directory_manager import DataDirectoryManager
from acquisition.fits_handler import FitsHandler
from acquisition.image_stacking import ImageStacking


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)

    print("Welcome to the NEOSSat Astronomy Image Analysis!")
    while True:
        print("Enter a valid email address to receive notifications:")
        email = input("Email: ")
        if "@" in email and "." in email:
            print(f"Email '{email}' accepted.")
            break
        else:
            print("Invalid email address. Please try again.")

    while True:
        print("Select a valid directory containing the data you want to analyze:")
        data_directory = input("Enter the path to the data directory: ")
        manager = DataDirectoryManager(data_directory)
        if manager.check_data_directory():
            print(f"Data directory '{data_directory}' found.")
            break
        else:
            print(
                f"Data directory '{data_directory}' does not exist. Please try again."
            )

    for filename in os.listdir(data_directory):
        if filename.endswith(".fits"):
            file_path = os.path.join(data_directory, filename)
            print(f"\nProcessing: {filename}")

            data_manager = DataManager(file_path)
            sky_coord = data_manager.get_coordinates()
            date_obs = data_manager.get_images_same_date()

            if sky_coord and date_obs:
                print(f"Coordinates Found: {sky_coord.to_string('hmsdms')}")
                print(f"Observation Date: {date_obs}")

                clean_name = filename.replace(".fits", "")
                download_path = os.path.join(base_dir, clean_name)
                os.makedirs(download_path, exist_ok=True)

                downloader = FitsHandler(sky_coord, date_obs)
                downloader.download_images_to_directory(download_path)
                preprocessor = ImageStacking(
                    download_path, data_manager, date_obs, results_dir
                )
                preprocessor.stack_images()

                print(f"Cleaning up temporary folder: {download_path}")
                shutil.rmtree(download_path)
            data_manager.fits_image.close()


if __name__ == "__main__":
    main()
