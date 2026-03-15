import pytest
import typer

from acquisition.directory_manager import DataDirectoryManager


def test_validate_data_directory_valid(tmp_path):
    result = DataDirectoryManager.validate_data_directory(str(tmp_path))
    assert result == str(tmp_path)


def test_validate_data_directory_invalid():
    with pytest.raises(typer.BadParameter):
        DataDirectoryManager.validate_data_directory("/invalid/directory/path")
