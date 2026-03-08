import os


class DataDirectoryManager:
    def __init__(self, data_directory):
        self.data_directory = data_directory

    def check_data_directory(self):
        return os.path.exists(self.data_directory)
