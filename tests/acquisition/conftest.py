from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from astropy.io import fits


@pytest.fixture
def sample_fits_image(tmp_path):
    """
    Sample FITS file for testing.
    """
    data = np.zeros((100, 100))
    hdu = fits.PrimaryHDU(data)
    hdu.header["RA"] = 120.5
    hdu.header["DEC"] = 45.3

    file_path = tmp_path / "sample.fits"
    hdu.writeto(file_path)

    return str(file_path)


@pytest.fixture
def mock_cadc():
    """
    Fixture to mock the CADC client.
    """
    obs_id = "NEOSSAT_CORD_001"

    row = MagicMock()
    row.__getitem__ = MagicMock(return_value=obs_id)

    results = MagicMock()
    results.__len__ = MagicMock(return_value=1)
    results.__getitem__ = MagicMock(
        side_effect=lambda key: (
            [obs_id]
            if key == "observationID"
            else (
                results
                if isinstance(key, list)
                else results if isinstance(key, slice) else row
            )
        )
    )

    # Write a real FITS file to dst so os.listdir picks it up
    def fake_move(src, dst):
        fits.PrimaryHDU(data=np.zeros((10, 10))).writeto(dst)

    with (
        patch("acquisition.fits_handler.Cadc") as MockCadc,
        patch(
            "acquisition.fits_handler.download_file",
            return_value="/tmp/fake_download.fits",
        ),
        patch("acquisition.fits_handler.shutil.move", side_effect=fake_move),
    ):
        mock_instance = MockCadc.return_value
        mock_instance.query_region.return_value = results
        mock_instance.get_data_urls.return_value = ["http://fake/NEOSSAT_CORD_001.fits"]
        yield mock_instance
