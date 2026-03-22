from unittest.mock import MagicMock, patch

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.table import Table

from tasks.stars.star_detection import StarDetection


def test_star_detection_run(tmp_path):

    image = np.zeros((100, 100))
    header = {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN"}

    fake_catalog_obj = MagicMock()
    fake_catalog_obj.coord = SkyCoord(ra=10 * u.deg, dec=20 * u.deg)
    fake_catalog_obj.object_id = "TEST_OBJ"
    fake_catalog_obj.otype = "star"

    fake_catalog = [fake_catalog_obj]

    fake_sources = Table(
        {
            "xcentroid": [10.0],
            "ycentroid": [20.0],
            "flux": [1000.0],
        }
    )

    with (
        patch(
            "tasks.stars.star_detection.query_simbad_skycoord",
            return_value=fake_catalog,
        ),
        patch("tasks.stars.star_detection.DAOStarFinder") as mock_dao,
        patch("tasks.stars.star_detection.generate_heatmap"),
    ):

        mock_instance = MagicMock()
        mock_instance.return_value = fake_sources
        mock_dao.return_value = mock_instance

        detector = StarDetection()
        result = detector.run(image, header, tmp_path)

    assert result["stars_detected"] == 1

    assert (tmp_path / "star_detection_results.csv").exists()
    assert (tmp_path / "detected_stars_img.png").exists()
    assert (tmp_path / "detected_stars_map.png").exists()
    assert (tmp_path / "region_catalog_map.png").exists()
