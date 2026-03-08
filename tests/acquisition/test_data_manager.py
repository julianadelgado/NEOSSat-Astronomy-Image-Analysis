import pytest
from acquisition.data_manager import DataManager

def test_load_fits_image_valid(sample_fits_image):
    dm = DataManager(sample_fits_image)
    assert dm.fits_image is not None
    assert len(dm.fits_image) > 0

def test_load_fits_image_invalid():
    dm = DataManager("/invalid/file/path.fits")
    assert dm.fits_image is None

def test_get_coordinates_valid(sample_fits_image):
    dm = DataManager(sample_fits_image)
    coords = dm.get_coordinates(dm.fits_image)
    assert coords is not None
    assert coords.ra.deg == 120.5
    assert coords.dec.deg == 45.3