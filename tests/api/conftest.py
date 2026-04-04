import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS


@pytest.fixture
def sample_fits_file_with_wcs(tmp_path):
    """
    Create a sample FITS file with WCS header for testing.
    """
    # Create sample data
    data = np.random.rand(100, 100).astype(np.float32) * 1000
    
    # Create FITS HDU with proper header
    hdu = fits.PrimaryHDU(data)
    
    # Add basic FITS headers
    hdu.header["SIMPLE"] = True
    hdu.header["BITPIX"] = -32
    hdu.header["NAXIS"] = 2
    hdu.header["NAXIS1"] = 100
    hdu.header["NAXIS2"] = 100
    
    # Add WCS headers
    hdu.header["CTYPE1"] = "RA---TAN"
    hdu.header["CTYPE2"] = "DEC--TAN"
    hdu.header["CRVAL1"] = 150.0  # RA at reference pixel
    hdu.header["CRVAL2"] = 2.0    # Dec at reference pixel
    hdu.header["CRPIX1"] = 50.0   # Reference pixel X
    hdu.header["CRPIX2"] = 50.0   # Reference pixel Y
    hdu.header["CDELT1"] = -0.001 # Degrees per pixel
    hdu.header["CDELT2"] = 0.001  # Degrees per pixel
    
    # Add observation metadata
    hdu.header["DATE-OBS"] = "2024-01-15T12:30:45"
    hdu.header["MODE"] = "16 - FINE_POINT"
    hdu.header["RA"] = 150.0
    hdu.header["DEC"] = 2.0
    
    file_path = tmp_path / "test_image.fits"
    hdu.writeto(file_path)
    
    return file_path


@pytest.fixture
def sample_fits_data_and_header():
    """
    Create sample FITS data and header for testing without file I/O.
    """
    data = np.random.rand(100, 100).astype(np.float32) * 1000
    
    header = fits.Header()
    header["SIMPLE"] = True
    header["BITPIX"] = -32
    header["NAXIS"] = 2
    header["NAXIS1"] = 100
    header["NAXIS2"] = 100
    header["CTYPE1"] = "RA---TAN"
    header["CTYPE2"] = "DEC--TAN"
    header["CRVAL1"] = 150.0
    header["CRVAL2"] = 2.0
    header["CRPIX1"] = 50.0
    header["CRPIX2"] = 50.0
    header["CDELT1"] = -0.001
    header["CDELT2"] = 0.001
    header["DATE-OBS"] = "2024-01-15T12:30:45"
    header["MODE"] = "16 - FINE_POINT"
    
    return data, header


@pytest.fixture
def mock_streak_detector_results():
    """
    Mock results from streak detector.
    """
    return {
        "streaks": [
            {
                "class": "0",
                "confidence": 0.85,
                "box": [0.5, 0.5, 0.1, 0.2],
                "world_coords": {
                    "ra_deg": 150.123,
                    "dec_deg": 2.456,
                    "ra_hms": "10:00:29.52",
                    "dec_dms": "+02:27:21.6"
                }
            },
            {
                "class": "0",
                "confidence": 0.72,
                "box": [0.3, 0.7, 0.15, 0.25],
            }
        ]
    }


@pytest.fixture
def mock_star_detection_results():
    """
    Mock results from star detection.
    """
    return {
        "stars_detected": 42
    }


@pytest.fixture
def mock_image_stacking_results():
    """
    Mock results from image stacking.
    """
    return {
        "status": "completed",
        "date_obs": "2024-01-15",
        "images_path": "data/"
    }
