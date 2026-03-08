import os
from unittest.mock import MagicMock

from acquisition.fits_handler import FitsHandler


def test_download_images_to_directory_valid(mock_cadc, tmp_path):
    fits_handler = FitsHandler(MagicMock(), "2023-01-01")
    fits_handler.download_images_to_directory(str(tmp_path))

    downloaded_files = [f for f in os.listdir(tmp_path) if f.endswith(".fits")]
    assert len(downloaded_files) > 0


def test_download_images_to_directory_invalid(tmp_path):
    sky_coord = "invalid coordinates"
    fits_handler = FitsHandler(sky_coord, None)

    fits_handler.download_images_to_directory(str(tmp_path))

    downloaded_files = [f for f in os.listdir(tmp_path) if f.endswith(".fits")]
    assert len(downloaded_files) == 0
