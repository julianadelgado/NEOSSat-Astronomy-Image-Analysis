import pytest
import typer

from cli.validator import validate_data_directory


def test_validate_data_directory_valid(tmp_path):
    result = validate_data_directory(str(tmp_path))
    assert result == str(tmp_path)


def test_validate_data_directory_invalid():
    with pytest.raises(typer.BadParameter):
        validate_data_directory("/invalid/directory/path")
