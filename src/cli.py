import os
from core.directory_manager import DataDirectoryManager
from core.fits_handler import FitsHandler
from core.data_manager import DataManager

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
                
                downloader = FitsHandler(sky_coord)
                downloader.download_images_to_directory(save_path)
            
            data_manager.fits_image.close()
        
if __name__ == '__main__':
    main()