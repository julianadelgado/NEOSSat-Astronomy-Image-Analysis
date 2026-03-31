import numpy as np
from astropy.io import fits

from handlers.data_manager import DataManager


def test_load_fits_image_valid(sample_fits_image):
    dm = DataManager(sample_fits_image)
    assert dm.fits_image is not None
    assert len(dm.fits_image) > 0


def test_load_fits_image_invalid():
    dm = DataManager("/invalid/file/path.fits")
    assert dm.fits_image is None


def test_is_fits_correct_mode_valid(sample_fits_image):
    dm = DataManager(sample_fits_image)
    assert dm.is_fits_correct_mode() is True


def test_is_fits_correct_mode_wrong_mode(tmp_path):
    hdu = fits.PrimaryHDU(np.zeros((10, 10)))
    hdu.header["MODE"] = "99 - UNKNOWN"
    path = tmp_path / "wrong_mode.fits"
    hdu.writeto(path)
    dm = DataManager(str(path))
    assert dm.is_fits_correct_mode() is False


def test_is_fits_correct_mode_no_image():
    dm = DataManager("/invalid/path.fits")
    assert dm.is_fits_correct_mode() is False


def test_get_coordinates_valid(sample_fits_image):
    dm = DataManager(sample_fits_image)
    coords = dm.get_coordinates()
    assert coords is not None
    assert coords.ra.deg == 120.5
    assert coords.dec.deg == 45.3


def test_get_coordinates_missing(tmp_path):
    hdu = fits.PrimaryHDU(np.zeros((10, 10)))
    path = tmp_path / "no_coords.fits"
    hdu.writeto(path)
    dm = DataManager(str(path))
    assert dm.get_coordinates() is None


def test_get_coordinates_no_image():
    dm = DataManager("/invalid/path.fits")
    assert dm.get_coordinates() is None


def test_get_images_same_date_valid(sample_fits_image):
    dm = DataManager(sample_fits_image)
    assert dm.get_images_same_date() == "2021-05-19"


def test_get_images_same_date_missing(tmp_path):
    hdu = fits.PrimaryHDU(np.zeros((10, 10)))
    path = tmp_path / "no_date.fits"
    hdu.writeto(path)
    dm = DataManager(str(path))
    assert dm.get_images_same_date() is None


def test_get_images_same_date_no_image():
    dm = DataManager("/invalid/path.fits")
    assert dm.get_images_same_date() is None
