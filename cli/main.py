import os
from acquisition.directory_manager import DataDirectoryManager
from acquisition.fits_handler import FitsHandler
from acquisition.data_manager import DataManager

def main():
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
                os.makedirs(clean_name, exist_ok=True)
                
                downloader = FitsHandler(sky_coord)
                downloader.download_images_to_directory(clean_name)
            data_manager.fits_image.close()
        
if __name__ == '__main__':
    main()