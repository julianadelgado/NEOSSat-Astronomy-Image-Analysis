from unittest.mock import MagicMock

import numpy as np
import pytest
from astropy.io import fits

from tasks.stacking.image_stacking import ImageStacking


@pytest.fixture
def sample_fits_file(tmp_path):
    """Create a minimal FITS file with DATE-OBS and MODE headers."""
    data = np.random.randint(0, 1000, (64, 64), dtype=np.uint16)
    hdu = fits.PrimaryHDU(data.astype(np.float32))
    hdu.header["DATE-OBS"] = "2023-01-01T00:00:00"
    hdu.header["MODE"] = "16 - FINE_POINT"
    path = str(tmp_path / "reference.fits")
    hdu.writeto(path)
    return path


@pytest.fixture
def extra_fits_file(tmp_path):
    """Create a second FITS file for the same date."""
    data = np.random.randint(0, 1000, (64, 64), dtype=np.uint16)
    hdu = fits.PrimaryHDU(data.astype(np.float32))
    hdu.header["DATE-OBS"] = "2023-01-01T00:05:00"
    hdu.header["MODE"] = "16 - FINE_POINT"
    path = str(tmp_path / "extra.fits")
    hdu.writeto(path)
    return path


@pytest.fixture
def wrong_date_fits_file(tmp_path):
    """Create a FITS file with a different date."""
    data = np.random.randint(0, 1000, (64, 64), dtype=np.uint16)
    hdu = fits.PrimaryHDU(data.astype(np.float32))
    hdu.header["DATE-OBS"] = "2023-06-15T00:00:00"
    hdu.header["MODE"] = "16 - FINE_POINT"
    path = str(tmp_path / "wrong_date.fits")
    hdu.writeto(path)
    return path


@pytest.fixture
def wrong_mode_fits_file(tmp_path):
    """Create a FITS file with a disallowed MODE header."""
    data = np.random.randint(0, 1000, (64, 64), dtype=np.uint16)
    hdu = fits.PrimaryHDU(data.astype(np.float32))
    hdu.header["DATE-OBS"] = "2023-01-01T00:00:00"
    hdu.header["MODE"] = "01 - STANDBY"
    path = str(tmp_path / "wrong_mode.fits")
    hdu.writeto(path)
    return path


@pytest.fixture
def mock_data_manager(sample_fits_file):
    """Return a MagicMock that mimics DataManager."""
    dm = MagicMock()
    dm.file_path = sample_fits_file
    dm.fits_to_png = MagicMock()
    return dm


@pytest.fixture
def image_stacking(tmp_path, mock_data_manager, sample_fits_file):
    """Return an ImageStacking instance pointing at tmp_path."""
    return ImageStacking(
        images_path=str(tmp_path),
        data_manager=mock_data_manager,
        date_obs="2023-01-01",
        results_dir=str(tmp_path),
    )
