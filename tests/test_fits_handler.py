import os
import pytest
from core.fits_handler import FitsHandler
from unittest.mock import MagicMock


def test_download_images_to_directory_valid(mock_cadc, tmp_path):
    fits_handler = FitsHandler(MagicMock())
    fits_handler.download_images_to_directory(str(tmp_path))

    downloaded_files = [f for f in os.listdir(tmp_path) if f.endswith('.fits')]
    assert len(downloaded_files) > 0


def test_download_images_to_directory_invalid(tmp_path):
    sky_coord = "invalid coordinates"
    fits_handler = FitsHandler(sky_coord)

    fits_handler.download_images_to_directory(str(tmp_path))

    downloaded_files = [f for f in os.listdir(tmp_path) if f.endswith('.fits')]
    assert len(downloaded_files) == 0