import pytest
from acquisition.directory_manager import DataDirectoryManager


def test_check_data_directory_valid(tmp_path):
    dir_manager = DataDirectoryManager(str(tmp_path))
    assert dir_manager.check_data_directory() == True

def test_check_data_directory_invalid():
    dir_manager = DataDirectoryManager("/invalid/directory/path")
    assert dir_manager.check_data_directory() == False