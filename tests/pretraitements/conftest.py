import pytest
import numpy as np
from astropy.io import fits


@pytest.fixture
def sample_fits_file(tmp_path):
    """
    Génère un fichier FITS pour les tests d’intégration.
    """
    data = np.zeros((20, 20))
    hdu = fits.PrimaryHDU(data)
    hdu.header["SIMPLE"] = True

    file_path = tmp_path / "sample.fits"
    hdu.writeto(file_path)

    return file_path


@pytest.fixture
def fake_image_and_header():
    image = np.zeros((10, 10))
    header = {"SIMPLE": True}
    return image, header
